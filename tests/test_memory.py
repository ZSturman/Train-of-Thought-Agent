from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from location_agent.memory import MemoryStore
from location_agent.models import NormalizedObservation


class MemoryStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.memory_path = Path(self.temporary_directory.name) / "location_memory.json"

    def test_blank_memory_file_bootstraps(self) -> None:
        self.memory_path.write_text("", encoding="utf-8")
        store = MemoryStore(self.memory_path)

        self.assertEqual({}, store.data["locations_by_observation"])
        self.assertEqual(1.0, store.guess_threshold)

    def test_learn_and_reload_persists_location(self) -> None:
        store = MemoryStore(self.memory_path)
        observation = NormalizedObservation.parse("0.25")

        _, learned = store.learn_location(observation, "kitchen")
        reloaded = MemoryStore(self.memory_path)
        recalled = reloaded.lookup(NormalizedObservation.parse("0.250000"))

        self.assertIsNotNone(recalled)
        self.assertEqual(learned.location_id, recalled.location_id)
        self.assertEqual("kitchen", recalled.label)
        self.assertEqual(1, recalled.observation_count)

    def test_normalized_lookup_reuses_same_key(self) -> None:
        store = MemoryStore(self.memory_path)
        store.learn_location(NormalizedObservation.parse("0.25"), "hallway")

        record = store.lookup(NormalizedObservation.parse("0.250000"))

        self.assertIsNotNone(record)
        self.assertEqual("0.250000", record.observation_key)
        self.assertEqual("hallway", record.label)


if __name__ == "__main__":
    unittest.main()
