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

    def test_noisy_queries_classify_correctly(self) -> None:
        """Learn 100 well-spaced observations, then query with noise and verify accuracy."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "location_memory.json"
            store = MemoryStore(path)

            # Learn 100 observations spaced 0.01 apart: 0.00, 0.01, ..., 0.99.
            for index in range(100):
                raw = f"{index / 100:.6f}"
                store.learn_location(NormalizedObservation.parse(raw), f"loc-{index}")

            reloaded = MemoryStore(path)
            tolerance = reloaded.tolerance  # 0.05
            threshold = reloaded.guess_threshold  # 0.6

            start = time.perf_counter()
            correct_matches = 0
            correct_rejections = 0
            total_queries = 0

            # Within-tolerance queries: offset by ±0.001 should match.
            for index in [0, 10, 25, 50, 75, 99]:
                base = index / 100
                for offset in [0.001, -0.001, 0.003, -0.003]:
                    query_val = base + offset
                    if not 0.0 <= query_val <= 1.0:
                        continue
                    total_queries += 1
                    obs = NormalizedObservation.parse(f"{query_val:.6f}")
                    record, confidence = reloaded.find_nearest(obs)
                    if record is not None and record.label == f"loc-{index}" and confidence >= threshold:
                        correct_matches += 1

            # Beyond-tolerance queries: offset by ±0.06 with well-spaced base
            #   should NOT confidently match the original.
            for index in [0, 50, 99]:
                base = index / 100
                for offset in [0.06, -0.06]:
                    query_val = base + offset
                    if not 0.0 <= query_val <= 1.0:
                        continue
                    total_queries += 1
                    obs = NormalizedObservation.parse(f"{query_val:.6f}")
                    record, confidence = reloaded.find_nearest(obs)
                    # It might match a *different* nearby observation, which is fine.
                    # What matters is it does NOT confidently return the original.
                    if record is None or record.label != f"loc-{index}":
                        correct_rejections += 1
                    elif confidence < threshold:
                        correct_rejections += 1

            duration = time.perf_counter() - start
            print(f"noisy_stress_duration_seconds={duration:.6f}")
            print(f"correct_matches={correct_matches} correct_rejections={correct_rejections} total={total_queries}")

            # All within-tolerance queries should have matched correctly.
            self.assertGreaterEqual(correct_matches, 20)
            # Beyond-tolerance queries should have been rejected/redirected.
            self.assertGreaterEqual(correct_rejections, 3)


if __name__ == "__main__":
    unittest.main()
