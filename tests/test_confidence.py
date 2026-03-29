from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from location_agent.memory import MemoryStore
from location_agent.models import (
    DEFAULT_TOLERANCE,
    NormalizedObservation,
    distance_to_interval,
    distance_to_confidence,
    reinforced_confidence,
    scalar_distance,
)


class ScalarDistanceTests(unittest.TestCase):
    def test_same_value_returns_zero(self) -> None:
        self.assertAlmostEqual(scalar_distance(0.5, 0.5), 0.0)

    def test_symmetric(self) -> None:
        self.assertAlmostEqual(scalar_distance(0.3, 0.7), scalar_distance(0.7, 0.3))

    def test_known_distance(self) -> None:
        self.assertAlmostEqual(scalar_distance(0.25, 0.30), 0.05)


class DistanceToIntervalTests(unittest.TestCase):
    def test_inside_interval_returns_zero(self) -> None:
        self.assertAlmostEqual(distance_to_interval(0.28, 0.1, 0.3), 0.0)

    def test_below_interval_returns_distance_to_lower_bound(self) -> None:
        self.assertAlmostEqual(distance_to_interval(0.05, 0.1, 0.3), 0.05)

    def test_above_interval_returns_distance_to_upper_bound(self) -> None:
        self.assertAlmostEqual(distance_to_interval(0.34, 0.1, 0.3), 0.04)


class DistanceToConfidenceTests(unittest.TestCase):
    def test_zero_distance_gives_full_confidence(self) -> None:
        self.assertAlmostEqual(distance_to_confidence(0.0, DEFAULT_TOLERANCE), 1.0)

    def test_at_tolerance_gives_floor(self) -> None:
        self.assertAlmostEqual(distance_to_confidence(DEFAULT_TOLERANCE, DEFAULT_TOLERANCE), 0.5)

    def test_half_tolerance_gives_midpoint(self) -> None:
        self.assertAlmostEqual(
            distance_to_confidence(DEFAULT_TOLERANCE / 2, DEFAULT_TOLERANCE),
            0.75,
        )

    def test_beyond_tolerance_gives_zero(self) -> None:
        self.assertAlmostEqual(distance_to_confidence(0.1, DEFAULT_TOLERANCE), 0.0)

    def test_negative_distance_gives_zero(self) -> None:
        self.assertAlmostEqual(distance_to_confidence(-0.01, DEFAULT_TOLERANCE), 0.0)

    def test_zero_tolerance_gives_zero(self) -> None:
        self.assertAlmostEqual(distance_to_confidence(0.01, 0.0), 0.0)


class FindNearestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.memory_path = Path(self.temporary_directory.name) / "location_memory.json"

    def _canonical_name(self, store: MemoryStore, model) -> str:
        return store.snapshot_location(model)["canonical_name"]

    def test_exact_match_returns_high_confidence(self) -> None:
        store = MemoryStore(self.memory_path)
        store.learn_location(NormalizedObservation.parse("0.25"), "kitchen")

        model, confidence = store.find_nearest(NormalizedObservation.parse("0.250000"))

        self.assertIsNotNone(model)
        self.assertEqual("kitchen", self._canonical_name(store, model))
        self.assertAlmostEqual(confidence, 1.0)

    def test_within_tolerance_returns_graded_confidence(self) -> None:
        store = MemoryStore(self.memory_path)
        store.learn_location(NormalizedObservation.parse("0.25"), "kitchen")

        model, confidence = store.find_nearest(NormalizedObservation.parse("0.253"))

        self.assertIsNotNone(model)
        self.assertEqual("kitchen", self._canonical_name(store, model))
        self.assertGreater(confidence, 0.5)
        self.assertLess(confidence, 1.0)

    def test_beyond_tolerance_returns_zero(self) -> None:
        store = MemoryStore(self.memory_path)
        store.learn_location(NormalizedObservation.parse("0.25"), "kitchen")

        model, confidence = store.find_nearest(NormalizedObservation.parse("0.40"))

        self.assertAlmostEqual(confidence, 0.0)
        self.assertIsNone(model)

    def test_nearest_wins_among_multiple(self) -> None:
        store = MemoryStore(self.memory_path)
        store.learn_location(NormalizedObservation.parse("0.20"), "lobby")
        store.learn_location(NormalizedObservation.parse("0.25"), "kitchen")

        model, _ = store.find_nearest(NormalizedObservation.parse("0.245"))

        self.assertIsNotNone(model)
        self.assertEqual("kitchen", self._canonical_name(store, model))

    def test_equidistant_returns_one_deterministically(self) -> None:
        store = MemoryStore(self.memory_path)
        store.learn_location(NormalizedObservation.parse("0.20"), "lobby")
        store.learn_location(NormalizedObservation.parse("0.24"), "kitchen")

        model, confidence = store.find_nearest(NormalizedObservation.parse("0.22"))

        self.assertIsNotNone(model)
        self.assertIn(self._canonical_name(store, model), {"lobby", "kitchen"})
        self.assertGreater(confidence, 0.5)

    def test_values_inside_learned_span_are_recognized(self) -> None:
        store = MemoryStore(self.memory_path)
        store.learn_location(NormalizedObservation.parse("0.10"), "Point one")
        store.reinforce_named_location(NormalizedObservation.parse("0.30"), "Point one")

        model, confidence = store.find_nearest(NormalizedObservation.parse("0.28"))

        self.assertIsNotNone(model)
        self.assertEqual("Point one", self._canonical_name(store, model))
        self.assertAlmostEqual(confidence, 1.0)

    def test_values_just_beyond_learned_span_decay_from_boundary(self) -> None:
        store = MemoryStore(self.memory_path)
        store.learn_location(NormalizedObservation.parse("0.10"), "Point one")
        store.reinforce_named_location(NormalizedObservation.parse("0.30"), "Point one")

        model, confidence = store.find_nearest(NormalizedObservation.parse("0.32"))

        self.assertIsNotNone(model)
        self.assertEqual("Point one", self._canonical_name(store, model))
        self.assertGreater(confidence, 0.5)


class FindNearCollisionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.memory_path = Path(self.temporary_directory.name) / "location_memory.json"

    def test_no_collision_for_distant_observation(self) -> None:
        store = MemoryStore(self.memory_path)
        store.learn_location(NormalizedObservation.parse("0.25"), "kitchen")

        collision = store.find_near_collision(NormalizedObservation.parse("0.80"))

        self.assertIsNone(collision)

    def test_collision_for_close_observation(self) -> None:
        store = MemoryStore(self.memory_path)
        store.learn_location(NormalizedObservation.parse("0.25"), "kitchen")

        collision = store.find_near_collision(NormalizedObservation.parse("0.252"))

        self.assertIsNotNone(collision)
        self.assertEqual("kitchen", store.snapshot_location(collision)["canonical_name"])


class ReinforcedConfidenceTests(unittest.TestCase):
    def test_zero_correct_count_returns_base(self) -> None:
        self.assertAlmostEqual(reinforced_confidence(0.8, 0), 0.8)

    def test_one_confirmation_boosts(self) -> None:
        self.assertAlmostEqual(reinforced_confidence(0.8, 1), 0.85)

    def test_multiple_confirmations_boost_more(self) -> None:
        self.assertAlmostEqual(reinforced_confidence(0.8, 4), 1.0)

    def test_boost_capped_at_max(self) -> None:
        self.assertAlmostEqual(reinforced_confidence(0.6, 100), 1.0)

    def test_zero_base_not_boosted(self) -> None:
        self.assertAlmostEqual(reinforced_confidence(0.0, 10), 0.0)

    def test_negative_base_not_boosted(self) -> None:
        self.assertAlmostEqual(reinforced_confidence(-0.1, 5), -0.1)


class ReinforcementIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.memory_path = Path(self.temporary_directory.name) / "location_memory.json"

    def test_confidence_increases_after_correct_guess(self) -> None:
        store = MemoryStore(self.memory_path)
        store.learn_location(NormalizedObservation.parse("0.25"), "kitchen")
        noisy = NormalizedObservation.parse("0.253")

        _, conf_before = store.find_nearest(noisy)
        exact = NormalizedObservation.parse("0.25")
        model, _ = store.find_nearest(exact)
        store.record_correct_guess(exact, matched_model=model)
        _, conf_after = store.find_nearest(noisy)

        self.assertGreater(conf_after, conf_before)

    def test_repeated_confirmations_keep_increasing(self) -> None:
        store = MemoryStore(self.memory_path)
        store.learn_location(NormalizedObservation.parse("0.25"), "kitchen")
        noisy = NormalizedObservation.parse("0.253")
        exact = NormalizedObservation.parse("0.25")

        confidences = []
        for _ in range(5):
            _, confidence = store.find_nearest(noisy)
            confidences.append(confidence)
            model, _ = store.find_nearest(exact)
            store.record_correct_guess(exact, matched_model=model)

        for index in range(1, len(confidences)):
            self.assertGreaterEqual(confidences[index], confidences[index - 1])


class MergeShiftsPrototypeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.memory_path = Path(self.temporary_directory.name) / "location_memory.json"

    def test_merge_shifts_prototype(self) -> None:
        store = MemoryStore(self.memory_path)
        _, model = store.learn_location(NormalizedObservation.parse("0.25"), "kitchen")

        old_model, new_model = store.merge_observation(model, 0.26)

        self.assertAlmostEqual(old_model.prototype, 0.25)
        self.assertAlmostEqual(new_model.prototype, 0.255)
        self.assertEqual(new_model.observation_count, 2)

    def test_confidence_computed_against_shifted_prototype(self) -> None:
        store = MemoryStore(self.memory_path)
        _, model = store.learn_location(NormalizedObservation.parse("0.25"), "kitchen")
        store.merge_observation(model, 0.26)

        found, confidence = store.find_nearest(NormalizedObservation.parse("0.255"))

        self.assertIsNotNone(found)
        self.assertEqual("kitchen", store.snapshot_location(found)["canonical_name"])
        self.assertAlmostEqual(confidence, 1.0)


class OutlierDetectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.memory_path = Path(self.temporary_directory.name) / "location_memory.json"

    def test_single_obs_model_uses_tolerance_as_floor(self) -> None:
        store = MemoryStore(self.memory_path)
        _, model = store.learn_location(NormalizedObservation.parse("0.25"), "kitchen")

        self.assertFalse(store.is_outlier(model, 0.35))
        self.assertTrue(store.is_outlier(model, 0.45))

    def test_model_with_tight_spread_detects_outlier(self) -> None:
        store = MemoryStore(self.memory_path)
        _, model = store.learn_location(NormalizedObservation.parse("0.25"), "kitchen")
        for value in [0.251, 0.249, 0.250, 0.251, 0.249]:
            _, model = store.merge_observation(model, value)

        self.assertLess(model.spread, 0.001)
        self.assertTrue(store.is_outlier(model, 0.45))
        self.assertFalse(store.is_outlier(model, 0.35))


if __name__ == "__main__":
    unittest.main()
