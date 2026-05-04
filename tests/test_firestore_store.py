"""Tests for FirestoreStore — the Firestore-backed MemoryStorage implementation.

Unit tests (no emulator required)
----------------------------------
These tests inject a mock Firestore client via the ``_client`` parameter so
that ``google-cloud-firestore`` need not be installed in the test environment.
They validate:

- Tenant-ID validation
- Full MemoryStorage protocol contract (learn → recognize → inspect → reset)
- State persistence across two FirestoreStore instances sharing the same
  backing document (simulates a server restart)

Emulator tests (require ``FIRESTORE_EMULATOR_HOST``)
-----------------------------------------------------
The ``@unittest.skipUnless`` marker skips these when the emulator is not
running. To run them locally::

    firebase emulators:start --only firestore &
    FIRESTORE_EMULATOR_HOST=localhost:8080 pytest tests/test_firestore_store.py -k emulator
"""

from __future__ import annotations

import copy
import os
import unittest
from unittest.mock import MagicMock

from location_agent._internal.firestore_store import FirestoreStore
from location_agent.models import NormalizedObservation
from location_agent.storage import MemoryStorage


# ---------------------------------------------------------------------------
# Minimal Firestore document / client stubs
# ---------------------------------------------------------------------------


class _MockDoc:
    """In-memory Firestore document stub."""

    def __init__(self) -> None:
        self._data: dict | None = None

    def get(self) -> object:
        data = self._data
        snap = MagicMock()
        snap.exists = data is not None
        snap.to_dict.return_value = copy.deepcopy(data) if data else {}
        return snap

    def set(self, data: dict) -> None:  # type: ignore[override]
        self._data = copy.deepcopy(data)


def _mock_client(doc: _MockDoc) -> MagicMock:
    """Build a MagicMock Firestore client that routes all chained calls to *doc*."""
    client = MagicMock()
    # tenants/{tenant_id}/memory/state → doc
    (
        client.collection.return_value.document.return_value.collection.return_value.document.return_value
    ) = doc
    return client


# ---------------------------------------------------------------------------
# Unit tests (no emulator)
# ---------------------------------------------------------------------------


class TestFirestoreStoreTenantValidation(unittest.TestCase):
    def test_invalid_tenant_slash_raises(self) -> None:
        with self.assertRaises(ValueError):
            FirestoreStore("bad/tenant", _client=MagicMock())

    def test_invalid_tenant_space_raises(self) -> None:
        with self.assertRaises(ValueError):
            FirestoreStore("bad tenant", _client=MagicMock())

    def test_tenant_too_long_raises(self) -> None:
        with self.assertRaises(ValueError):
            FirestoreStore("x" * 129, _client=MagicMock())

    def test_valid_tenant_id_accepted(self) -> None:
        doc = _MockDoc()
        store = FirestoreStore("valid-tenant_1", _client=_mock_client(doc))
        self.assertEqual(store.tenant_id, "valid-tenant_1")


class TestFirestoreStoreProtocol(unittest.TestCase):
    """Verify FirestoreStore satisfies the MemoryStorage protocol."""

    def _store(self, doc: _MockDoc | None = None) -> FirestoreStore:
        if doc is None:
            doc = _MockDoc()
        return FirestoreStore("tenant1", _client=_mock_client(doc))

    def test_satisfies_memory_storage_protocol(self) -> None:
        store = self._store()
        self.assertIsInstance(store, MemoryStorage)

    def test_learn_location_returns_model(self) -> None:
        store = self._store()
        obs = NormalizedObservation.parse("0.25")
        _, model = store.learn_location(obs, "kitchen")
        self.assertEqual(store.snapshot_location(model)["canonical_name"], "kitchen")

    def test_find_nearest_after_learn(self) -> None:
        store = self._store()
        obs = NormalizedObservation.parse("0.25")
        store.learn_location(obs, "kitchen")
        found, confidence = store.find_nearest(NormalizedObservation.parse("0.253"))
        self.assertIsNotNone(found)
        self.assertGreater(confidence, 0.5)

    def test_guess_threshold_property(self) -> None:
        store = self._store()
        self.assertIsInstance(store.guess_threshold, float)
        self.assertGreater(store.guess_threshold, 0.0)

    def test_inspect_models_empty_on_fresh_store(self) -> None:
        store = self._store()
        self.assertEqual(store.inspect_models(), [])

    def test_inspect_models_returns_learned_locations(self) -> None:
        store = self._store()
        store.learn_location(NormalizedObservation.parse("0.1"), "alpha")
        store.learn_location(NormalizedObservation.parse("0.9"), "beta")
        models = store.inspect_models()
        self.assertEqual(len(models), 2)
        names = {m["canonical_name"] for m in models}
        self.assertEqual(names, {"alpha", "beta"})

    def test_reset_memory_clears_all(self) -> None:
        store = self._store()
        store.learn_location(NormalizedObservation.parse("0.5"), "room")
        cleared = store.reset_memory()
        self.assertGreaterEqual(cleared, 1)
        self.assertEqual(store.inspect_models(), [])

    def test_lookup_by_id_returns_none_for_unknown(self) -> None:
        store = self._store()
        self.assertIsNone(store.lookup_by_id("loc-does-not-exist"))

    def test_record_correct_guess_reinforces_model(self) -> None:
        store = self._store()
        obs = NormalizedObservation.parse("0.4")
        _, model = store.learn_location(obs, "lounge")
        before_correct = model.correct_count
        _, updated = store.record_correct_guess(obs, matched_model=model)
        self.assertGreater(updated.correct_count, before_correct)


class TestFirestoreStorePersistence(unittest.TestCase):
    """State written by one FirestoreStore instance is visible to a second instance
    sharing the same backing document (simulates a process restart)."""

    def test_state_survives_new_instance(self) -> None:
        doc = _MockDoc()

        store1 = FirestoreStore("tenant1", _client=_mock_client(doc))
        store1.learn_location(NormalizedObservation.parse("0.25"), "kitchen")

        # A second instance loading from the same doc should see the state.
        store2 = FirestoreStore("tenant1", _client=_mock_client(doc))
        found, conf = store2.find_nearest(NormalizedObservation.parse("0.253"))
        self.assertIsNotNone(found)
        self.assertGreater(conf, 0.5)

    def test_reset_visible_to_new_instance(self) -> None:
        doc = _MockDoc()

        store1 = FirestoreStore("tenant1", _client=_mock_client(doc))
        store1.learn_location(NormalizedObservation.parse("0.25"), "kitchen")
        store1.reset_memory()

        store2 = FirestoreStore("tenant1", _client=_mock_client(doc))
        self.assertEqual(store2.inspect_models(), [])


# ---------------------------------------------------------------------------
# Emulator tests (skipped when FIRESTORE_EMULATOR_HOST is not set)
# ---------------------------------------------------------------------------

_EMULATOR = os.environ.get("FIRESTORE_EMULATOR_HOST", "")


@unittest.skipUnless(_EMULATOR, "FIRESTORE_EMULATOR_HOST not set — skipping emulator tests")
class TestFirestoreStoreEmulator(unittest.TestCase):
    """Integration tests against the Firestore emulator."""

    _PROJECT = "tot-test"

    def _store(self, tenant_id: str = "emulator-tenant") -> FirestoreStore:
        return FirestoreStore(tenant_id, project_id=self._PROJECT)

    def test_learn_and_recognize_via_emulator(self) -> None:
        store = self._store()
        store.reset_memory()
        obs = NormalizedObservation.parse("0.3")
        store.learn_location(obs, "emulator-kitchen")
        found, conf = store.find_nearest(NormalizedObservation.parse("0.303"))
        self.assertIsNotNone(found)
        self.assertGreater(conf, 0.5)

    def test_persistence_across_instances_via_emulator(self) -> None:
        tenant = "emulator-persist-test"
        s1 = self._store(tenant)
        s1.reset_memory()
        s1.learn_location(NormalizedObservation.parse("0.6"), "emulator-room")

        s2 = self._store(tenant)
        models = s2.inspect_models()
        self.assertEqual(len(models), 1)
        self.assertEqual(models[0]["canonical_name"], "emulator-room")


if __name__ == "__main__":
    unittest.main()
