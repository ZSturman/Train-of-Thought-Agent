from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from location_agent.memory import MemoryStore
from location_agent.models import (
    DEFAULT_TOLERANCE,
    NormalizedObservation,
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


class DistanceToConfidenceTests(unittest.TestCase):
    def test_zero_distance_gives_full_confidence(self) -> None:
        self.assertAlmostEqual(distance_to_confidence(0.0, DEFAULT_TOLERANCE), 1.0)

    def test_at_tolerance_gives_floor(self) -> None:
        self.assertAlmostEqual(distance_to_confidence(DEFAULT_TOLERANCE, DEFAULT_TOLERANCE), 0.5)

    def test_half_tolerance_gives_midpoint(self) -> None:
        self.assertAlmostEqual(
            distance_to_confidence(DEFAULT_TOLERANCE / 2, DEFAULT_TOLERANCE), 0.75
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

    def test_exact_match_returns_confidence_1(self) -> None:
        store = MemoryStore(self.memory_path)
        store.learn_location(NormalizedObservation.parse("0.25"), "kitchen")

        record, confidence = store.find_nearest(NormalizedObservation.parse("0.250000"))

        self.assertIsNotNone(record)
        self.assertEqual("kitchen", record.label)
        self.assertAlmostEqual(confidence, 1.0)

    def test_within_tolerance_returns_graded_confidence(self) -> None:
        store = MemoryStore(self.memory_path)
        store.learn_location(NormalizedObservation.parse("0.25"), "kitchen")

        record, confidence = store.find_nearest(NormalizedObservation.parse("0.253"))

        self.assertIsNotNone(record)
        self.assertEqual("kitchen", record.label)
        self.assertGreater(confidence, 0.5)
        self.assertLess(confidence, 1.0)

    def test_beyond_tolerance_returns_zero(self) -> None:
        store = MemoryStore(self.memory_path)
        store.learn_location(NormalizedObservation.parse("0.25"), "kitchen")

        record, confidence = store.find_nearest(NormalizedObservation.parse("0.40"))

        self.assertAlmostEqual(confidence, 0.0)
        self.assertIsNone(record)

    def test_nearest_wins_among_multiple(self) -> None:
        store = MemoryStore(self.memory_path)
        store.learn_location(NormalizedObservation.parse("0.20"), "lobby")
        store.learn_location(NormalizedObservation.parse("0.25"), "kitchen")

        record, confidence = store.find_nearest(NormalizedObservation.parse("0.245"))

        self.assertIsNotNone(record)
        self.assertEqual("kitchen", record.label)

    def test_equidistant_returns_one_deterministically(self) -> None:
        store = MemoryStore(self.memory_path)
        store.learn_location(NormalizedObservation.parse("0.20"), "lobby")
        store.learn_location(NormalizedObservation.parse("0.24"), "kitchen")

        # Query at 0.22 is equidistant from 0.20 and 0.24 (distance 0.02 each).
        record, confidence = store.find_nearest(NormalizedObservation.parse("0.22"))

        self.assertIsNotNone(record)
        self.assertIn(record.label, {"lobby", "kitchen"})
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
        self.assertEqual("kitchen", collision.label)


class ReinforcedConfidenceTests(unittest.TestCase):
    def test_zero_correct_count_returns_base(self) -> None:
        self.assertAlmostEqual(reinforced_confidence(0.8, 0), 0.8)

    def test_one_confirmation_boosts(self) -> None:
        self.assertAlmostEqual(reinforced_confidence(0.8, 1), 0.85)

    def test_multiple_confirmations_boost_more(self) -> None:
        self.assertAlmostEqual(reinforced_confidence(0.8, 4), 1.0)

    def test_boost_capped_at_max(self) -> None:
        # 100 confirmations should cap at boost of 0.4, so 0.6 + 0.4 = 1.0
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

        # Before any confirmations.
        _, conf_before = store.find_nearest(noisy)

        # Simulate a correct guess confirmation on the exact key.
        exact = NormalizedObservation.parse("0.25")
        store.record_correct_guess(exact)

        # After one confirmation, noisy confidence should be higher.
        _, conf_after = store.find_nearest(noisy)
        self.assertGreater(conf_after, conf_before)

    def test_repeated_confirmations_keep_increasing(self) -> None:
        store = MemoryStore(self.memory_path)
        store.learn_location(NormalizedObservation.parse("0.25"), "kitchen")
        noisy = NormalizedObservation.parse("0.253")
        exact = NormalizedObservation.parse("0.25")

        confidences = []
        for _ in range(5):
            _, conf = store.find_nearest(noisy)
            confidences.append(conf)
            store.record_correct_guess(exact)

        # Each successive confidence should be >= the previous.
        for i in range(1, len(confidences)):
            self.assertGreaterEqual(confidences[i], confidences[i - 1])


if __name__ == "__main__":
    unittest.main()
