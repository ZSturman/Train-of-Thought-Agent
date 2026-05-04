"""End-to-end HTTP API tests using FastAPI's TestClient.

These tests use an in-memory Agent per test (via dependency_overrides) so
they run without disk I/O and without a running server.
"""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

import location_agent.api as api_module
from location_agent.agent import Agent
from location_agent.api import app, get_agent
from location_agent.memory import MemoryStore

_API_KEY = "test-secret-key-for-ci"


def _fresh_agent(tmp_path: Path) -> Agent:
    store = MemoryStore(tmp_path / "memory.json")
    return Agent(store=store)


class ApiTestCase(unittest.TestCase):
    """Base class that wires a fresh in-memory agent and sets TOT_API_KEY."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.agent = _fresh_agent(Path(self.tmp.name))

        # Reset the module-level singleton so tests don't bleed into each other.
        api_module._agent_singleton = None

        app.dependency_overrides[get_agent] = lambda: self.agent
        os.environ["TOT_API_KEY"] = _API_KEY
        self.client = TestClient(app, raise_server_exceptions=True)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        os.environ.pop("TOT_API_KEY", None)
        api_module._agent_singleton = None

    def _headers(self) -> dict[str, str]:
        return {"X-API-Key": _API_KEY}


# ---------------------------------------------------------------------------
# Auth tests
# ---------------------------------------------------------------------------


class TestAuth(ApiTestCase):
    def test_missing_key_returns_401(self) -> None:
        r = self.client.get("/inspect")
        self.assertIn(r.status_code, (401, 403))

    def test_wrong_key_returns_401(self) -> None:
        r = self.client.get("/inspect", headers={"X-API-Key": "wrong"})
        self.assertEqual(r.status_code, 401)

    def test_correct_key_succeeds(self) -> None:
        r = self.client.get("/inspect", headers=self._headers())
        self.assertEqual(r.status_code, 200)

    def test_unconfigured_api_key_returns_503(self) -> None:
        os.environ.pop("TOT_API_KEY", None)
        r = self.client.get("/inspect", headers={"X-API-Key": "anything"})
        self.assertEqual(r.status_code, 503)


# ---------------------------------------------------------------------------
# /learn
# ---------------------------------------------------------------------------


class TestLearn(ApiTestCase):
    def test_learn_returns_location_id_and_label(self) -> None:
        r = self.client.post(
            "/learn",
            json={"value": 0.25, "label": "kitchen"},
            headers=self._headers(),
        )
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIn("location_id", body)
        self.assertEqual(body["label"], "kitchen")
        self.assertIn("snapshot", body)

    def test_learn_value_out_of_range_returns_422(self) -> None:
        r = self.client.post(
            "/learn",
            json={"value": 1.5, "label": "x"},
            headers=self._headers(),
        )
        self.assertEqual(r.status_code, 422)

    def test_learn_empty_label_returns_422(self) -> None:
        r = self.client.post(
            "/learn",
            json={"value": 0.5, "label": ""},
            headers=self._headers(),
        )
        self.assertEqual(r.status_code, 422)


# ---------------------------------------------------------------------------
# /recognize
# ---------------------------------------------------------------------------


class TestRecognize(ApiTestCase):
    def test_recognize_unknown_returns_is_known_false(self) -> None:
        r = self.client.post(
            "/recognize",
            json={"value": 0.5},
            headers=self._headers(),
        )
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.json()["is_known"])

    def test_recognize_known_returns_label(self) -> None:
        self.client.post(
            "/learn",
            json={"value": 0.25, "label": "kitchen"},
            headers=self._headers(),
        )
        r = self.client.post(
            "/recognize",
            json={"value": 0.253},
            headers=self._headers(),
        )
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertTrue(body["is_known"])
        self.assertEqual(body["label"], "kitchen")
        self.assertGreater(body["confidence"], 0.5)


# ---------------------------------------------------------------------------
# /confirm and /correct
# ---------------------------------------------------------------------------


class TestConfirmCorrect(ApiTestCase):
    def _learn(self, value: float, label: str) -> str:
        r = self.client.post(
            "/learn",
            json={"value": value, "label": label},
            headers=self._headers(),
        )
        return r.json()["location_id"]

    def test_confirm_known_location(self) -> None:
        loc_id = self._learn(0.3, "office")
        r = self.client.post(
            "/confirm",
            json={"value": 0.3, "location_id": loc_id},
            headers=self._headers(),
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn("location_id", r.json())

    def test_confirm_unknown_location_returns_404(self) -> None:
        r = self.client.post(
            "/confirm",
            json={"value": 0.3, "location_id": "loc-does-not-exist"},
            headers=self._headers(),
        )
        self.assertEqual(r.status_code, 404)

    def test_correct_relabels_location(self) -> None:
        loc_id = self._learn(0.7, "bedroom")
        r = self.client.post(
            "/correct",
            json={"value": 0.7, "location_id": loc_id, "new_label": "master bedroom"},
            headers=self._headers(),
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["canonical_name"], "master bedroom")

    def test_correct_unknown_location_returns_404(self) -> None:
        r = self.client.post(
            "/correct",
            json={"value": 0.7, "location_id": "loc-ghost", "new_label": "hallway"},
            headers=self._headers(),
        )
        self.assertEqual(r.status_code, 404)


# ---------------------------------------------------------------------------
# /inspect
# ---------------------------------------------------------------------------


class TestInspect(ApiTestCase):
    def test_inspect_empty_state(self) -> None:
        r = self.client.get("/inspect", headers=self._headers())
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIn("locations", body)
        self.assertEqual(body["locations"], [])

    def test_inspect_after_learn_includes_location(self) -> None:
        self.client.post(
            "/learn",
            json={"value": 0.1, "label": "lobby"},
            headers=self._headers(),
        )
        r = self.client.get("/inspect", headers=self._headers())
        body = r.json()
        self.assertEqual(len(body["locations"]), 1)
        self.assertEqual(body["locations"][0]["canonical_name"], "lobby")


# ---------------------------------------------------------------------------
# /reset
# ---------------------------------------------------------------------------


class TestReset(ApiTestCase):
    def test_reset_clears_learned_locations(self) -> None:
        self.client.post(
            "/learn",
            json={"value": 0.5, "label": "garage"},
            headers=self._headers(),
        )
        r = self.client.post("/reset", headers=self._headers())
        self.assertEqual(r.status_code, 200)
        self.assertGreaterEqual(r.json()["cleared"], 1)

        inspect = self.client.get("/inspect", headers=self._headers()).json()
        self.assertEqual(inspect["locations"], [])


# ---------------------------------------------------------------------------
# Full teach → recognize → inspect smoke
# ---------------------------------------------------------------------------


class TestEndToEndSmoke(ApiTestCase):
    def test_teach_recognize_inspect_curl_equivalent(self) -> None:
        """Mirrors the R3 acceptance-criteria curl smoke test."""
        # Learn
        learn_r = self.client.post(
            "/learn",
            json={"value": 0.25, "label": "kitchen"},
            headers=self._headers(),
        )
        self.assertEqual(learn_r.status_code, 200)

        # Recognize
        rec_r = self.client.post(
            "/recognize",
            json={"value": 0.253},
            headers=self._headers(),
        )
        self.assertEqual(rec_r.status_code, 200)
        self.assertTrue(rec_r.json()["is_known"])

        # Inspect
        ins_r = self.client.get("/inspect", headers=self._headers())
        self.assertEqual(ins_r.status_code, 200)
        self.assertEqual(len(ins_r.json()["locations"]), 1)


if __name__ == "__main__":
    unittest.main()
