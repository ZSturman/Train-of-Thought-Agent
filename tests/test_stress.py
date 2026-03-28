from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path

from location_agent.memory import MemoryStore
from location_agent.models import NormalizedObservation


class StressTests(unittest.TestCase):
    def test_store_handles_1000_unique_observations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "location_memory.json"
            store = MemoryStore(path)

            start = time.perf_counter()
            for index in range(1000):
                raw = f"{index / 1_000_000:.6f}"
                store.learn_location(NormalizedObservation.parse(raw), f"loc-{index}")
            reloaded = MemoryStore(path)
            sample_indexes = [0, 1, 17, 250, 999]
            labels = []
            for index in sample_indexes:
                raw = f"{index / 1_000_000:.6f}"
                record = reloaded.lookup(NormalizedObservation.parse(raw))
                self.assertIsNotNone(record)
                labels.append(record.label)
            duration = time.perf_counter() - start

            print(f"stress_duration_seconds={duration:.6f}")
            self.assertEqual(
                ["loc-0", "loc-1", "loc-17", "loc-250", "loc-999"],
                labels,
            )


if __name__ == "__main__":
    unittest.main()
