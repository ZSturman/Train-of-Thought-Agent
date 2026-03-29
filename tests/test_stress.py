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
                obs = NormalizedObservation.parse(raw)
                model, confidence = reloaded.find_nearest(obs)
                self.assertIsNotNone(model)
                labels.append(model.label)
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

            for index in range(100):
                raw = f"{index / 100:.6f}"
                store.learn_location(NormalizedObservation.parse(raw), f"loc-{index}")

            reloaded = MemoryStore(path)
            tolerance = reloaded.tolerance
            threshold = reloaded.guess_threshold

            start = time.perf_counter()
            correct_matches = 0
            correct_rejections = 0
            total_queries = 0

            for index in [0, 10, 25, 50, 75, 99]:
                base = index / 100
                for offset in [0.001, -0.001, 0.003, -0.003]:
                    query_val = base + offset
                    if not 0.0 <= query_val <= 1.0:
                        continue
                    total_queries += 1
                    obs = NormalizedObservation.parse(f"{query_val:.6f}")
                    model, confidence = reloaded.find_nearest(obs)
                    if model is not None and model.label == f"loc-{index}" and confidence >= threshold:
                        correct_matches += 1

            for index in [0, 50, 99]:
                base = index / 100
                for offset in [0.06, -0.06]:
                    query_val = base + offset
                    if not 0.0 <= query_val <= 1.0:
                        continue
                    total_queries += 1
                    obs = NormalizedObservation.parse(f"{query_val:.6f}")
                    model, confidence = reloaded.find_nearest(obs)
                    if model is None or model.label != f"loc-{index}":
                        correct_rejections += 1
                    elif confidence < threshold:
                        correct_rejections += 1

            duration = time.perf_counter() - start
            print(f"noisy_stress_duration_seconds={duration:.6f}")
            print(f"correct_matches={correct_matches} correct_rejections={correct_rejections} total={total_queries}")

            self.assertGreaterEqual(correct_matches, 20)
            self.assertGreaterEqual(correct_rejections, 3)

    def test_merge_stress_100_models_10_observations_each(self) -> None:
        """Create 100 models and merge 10 noisy observations into each."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "location_memory.json"
            store = MemoryStore(path)

            start = time.perf_counter()
            # Learn 100 well-spaced models: 0.001, 0.011, ..., 0.991.
            for index in range(100):
                base = 0.001 + index * 0.01
                obs = NormalizedObservation.parse(f"{base:.6f}")
                store.learn_location(obs, f"room-{index}")

            # Merge 10 noisy observations into each model.
            for index in range(100):
                base = 0.001 + index * 0.01
                model_id = None
                for merge_idx in range(10):
                    noisy = base + (merge_idx - 5) * 0.0001  # tiny offsets
                    noisy = max(0.0, min(1.0, noisy))
                    obs = NormalizedObservation.parse(f"{noisy:.6f}")
                    found_model, confidence = store.find_nearest(obs)
                    if found_model is not None and confidence >= store.guess_threshold:
                        old, new = store.merge_observation(found_model, noisy)
                        model_id = new.location_id

            duration = time.perf_counter() - start
            print(f"merge_stress_duration_seconds={duration:.6f}")

            # Verify all 100 models exist and have merged observations.
            models = store.inspect_models()
            self.assertEqual(100, len(models))
            for m in models:
                self.assertGreater(m["observation_count"], 1)


if __name__ == "__main__":
    unittest.main()
