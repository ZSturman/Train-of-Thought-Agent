from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from location_agent.memory import MemoryStore
from location_agent.models import NormalizedObservation, utc_now_iso


class MemoryStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.memory_path = Path(self.temporary_directory.name) / "location_memory.json"

    def test_blank_memory_file_bootstraps(self) -> None:
        self.memory_path.write_text("", encoding="utf-8")
        store = MemoryStore(self.memory_path)

        self.assertEqual({}, store.data["location_models"])
        self.assertEqual(0.6, store.guess_threshold)

    def test_learn_and_reload_persists_model(self) -> None:
        store = MemoryStore(self.memory_path)
        observation = NormalizedObservation.parse("0.25")

        _, learned = store.learn_location(observation, "kitchen")
        reloaded = MemoryStore(self.memory_path)
        recalled = reloaded.lookup_by_id(learned.location_id)

        self.assertIsNotNone(recalled)
        self.assertEqual(learned.location_id, recalled.location_id)
        self.assertEqual("kitchen", recalled.label)
        self.assertAlmostEqual(recalled.prototype, 0.25)
        self.assertEqual(1, recalled.observation_count)

    def test_find_nearest_after_learn(self) -> None:
        store = MemoryStore(self.memory_path)
        store.learn_location(NormalizedObservation.parse("0.25"), "hallway")

        model, confidence = store.find_nearest(NormalizedObservation.parse("0.250000"))

        self.assertIsNotNone(model)
        self.assertEqual("hallway", model.label)
        self.assertAlmostEqual(confidence, 1.0)


class SchemaMigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.memory_path = Path(self.temporary_directory.name) / "location_memory.json"

    def test_v2_to_v3_migration(self) -> None:
        v2_payload = {
            "schema_version": 2,
            "created_at": "2026-03-26T08:47:07+00:00",
            "updated_at": "2026-03-28T00:00:00+00:00",
            "confidence_policy": {
                "kind": "distance",
                "tolerance": 0.05,
                "guess_threshold": 0.6,
                "normalization_decimals": 6,
            },
            "locations_by_observation": {
                "0.250000": {
                    "location_id": "loc-oldkitchen",
                    "observation_key": "0.250000",
                    "observation_value": 0.25,
                    "label": "kitchen",
                    "observation_count": 3,
                    "guess_count": 2,
                    "correct_count": 1,
                    "incorrect_count": 1,
                    "first_seen_at": "2026-03-26T08:47:07+00:00",
                    "last_seen_at": "2026-03-28T00:00:00+00:00",
                },
                "0.900000": {
                    "location_id": "loc-oldlobby",
                    "observation_key": "0.900000",
                    "observation_value": 0.9,
                    "label": "lobby",
                    "observation_count": 1,
                    "guess_count": 0,
                    "correct_count": 0,
                    "incorrect_count": 0,
                    "first_seen_at": "2026-03-26T09:00:00+00:00",
                    "last_seen_at": "2026-03-26T09:00:00+00:00",
                },
            },
        }
        self.memory_path.write_text(json.dumps(v2_payload), encoding="utf-8")

        store = MemoryStore(self.memory_path)

        self.assertEqual(3, store.data["schema_version"])
        self.assertIn("location_models", store.data)
        self.assertNotIn("locations_by_observation", store.data)

        # Verify models were created correctly.
        models = store.inspect_models()
        self.assertEqual(2, len(models))
        labels = {m["label"] for m in models}
        self.assertEqual({"kitchen", "lobby"}, labels)

        kitchen_model = next(m for m in models if m["label"] == "kitchen")
        self.assertAlmostEqual(kitchen_model["prototype"], 0.25)
        self.assertEqual(kitchen_model["observation_count"], 3)

    def test_v1_to_v3_migration(self) -> None:
        v1_payload = {
            "schema_version": 1,
            "created_at": "2026-03-26T08:47:07+00:00",
            "updated_at": "2026-03-26T08:47:07+00:00",
            "confidence_policy": {
                "kind": "exact",
                "guess_threshold": 1.0,
                "normalization_decimals": 6,
            },
            "locations_by_observation": {
                "0.330000": {
                    "location_id": "loc-office",
                    "observation_key": "0.330000",
                    "observation_value": 0.33,
                    "label": "office",
                    "observation_count": 1,
                    "guess_count": 0,
                    "correct_count": 0,
                    "incorrect_count": 0,
                    "first_seen_at": "2026-03-26T08:47:07+00:00",
                    "last_seen_at": "2026-03-26T08:47:07+00:00",
                },
            },
        }
        self.memory_path.write_text(json.dumps(v1_payload), encoding="utf-8")

        store = MemoryStore(self.memory_path)

        self.assertEqual(3, store.data["schema_version"])
        models = store.inspect_models()
        self.assertEqual(1, len(models))
        self.assertEqual("office", models[0]["label"])


class InspectModelsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.memory_path = Path(self.temporary_directory.name) / "location_memory.json"

    def test_empty_store_returns_empty_list(self) -> None:
        store = MemoryStore(self.memory_path)
        self.assertEqual([], store.inspect_models())

    def test_inspect_returns_correct_fields(self) -> None:
        store = MemoryStore(self.memory_path)
        store.learn_location(NormalizedObservation.parse("0.25"), "kitchen")
        store.learn_location(NormalizedObservation.parse("0.90"), "lobby")

        models = store.inspect_models()
        self.assertEqual(2, len(models))
        for m in models:
            self.assertIn("location_id", m)
            self.assertIn("label", m)
            self.assertIn("prototype", m)
            self.assertIn("spread", m)
            self.assertIn("observation_count", m)


class ResetMemoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.memory_path = Path(self.temporary_directory.name) / "location_memory.json"

    def test_reset_clears_all_models(self) -> None:
        store = MemoryStore(self.memory_path)
        store.learn_location(NormalizedObservation.parse("0.25"), "kitchen")
        store.learn_location(NormalizedObservation.parse("0.90"), "lobby")
        self.assertEqual(2, len(store.inspect_models()))

        count = store.reset_memory()

        self.assertEqual(2, count)
        self.assertEqual([], store.inspect_models())

    def test_reset_returns_zero_on_empty_store(self) -> None:
        store = MemoryStore(self.memory_path)
        count = store.reset_memory()
        self.assertEqual(0, count)
        self.assertEqual([], store.inspect_models())

    def test_reset_persists_across_reload(self) -> None:
        store = MemoryStore(self.memory_path)
        store.learn_location(NormalizedObservation.parse("0.50"), "hallway")
        store.reset_memory()

        reloaded = MemoryStore(self.memory_path)
        self.assertEqual([], reloaded.inspect_models())
        self.assertEqual(3, reloaded.data["schema_version"])

    def test_reset_preserves_schema_version(self) -> None:
        store = MemoryStore(self.memory_path)
        store.learn_location(NormalizedObservation.parse("0.25"), "kitchen")
        store.reset_memory()
        self.assertEqual(3, store.data["schema_version"])
        self.assertIn("confidence_policy", store.data)


if __name__ == "__main__":
    unittest.main()
