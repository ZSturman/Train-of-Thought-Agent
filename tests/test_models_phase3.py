from __future__ import annotations

import math
import unittest

from location_agent.models import (
    LocationModel,
    LocationRecord,
    compute_spread,
    utc_now_iso,
)


class ComputeSpreadTests(unittest.TestCase):
    def test_empty_list_returns_zero(self) -> None:
        self.assertAlmostEqual(compute_spread([]), 0.0)

    def test_single_value_returns_zero(self) -> None:
        self.assertAlmostEqual(compute_spread([0.5]), 0.0)

    def test_two_identical_values_returns_zero(self) -> None:
        self.assertAlmostEqual(compute_spread([0.3, 0.3]), 0.0)

    def test_known_spread(self) -> None:
        # values: [2, 4, 4, 4, 5, 5, 7, 9], mean=5, pop-stddev=2.0
        values = [2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]
        self.assertAlmostEqual(compute_spread(values), 2.0)

    def test_two_values(self) -> None:
        # [0.2, 0.4] → mean=0.3, pop stdev = sqrt(((0.1)^2 + (0.1)^2)/2) = 0.1
        self.assertAlmostEqual(compute_spread([0.2, 0.4]), 0.1)


class LocationModelCreationTests(unittest.TestCase):
    def test_single_observation_model(self) -> None:
        ts = utc_now_iso()
        model = LocationModel(
            location_id="loc-abc",
            label="kitchen",
            prototype=0.25,
            observation_values=(0.25,),
            observation_count=1,
            spread=0.0,
            guess_count=0,
            correct_count=0,
            incorrect_count=0,
            first_seen_at=ts,
            last_seen_at=ts,
        )
        self.assertAlmostEqual(model.prototype, 0.25)
        self.assertAlmostEqual(model.spread, 0.0)
        self.assertEqual(model.observation_count, 1)
        self.assertEqual(model.observation_values, (0.25,))

    def test_serialization_round_trip(self) -> None:
        ts = utc_now_iso()
        model = LocationModel(
            location_id="loc-xyz",
            label="lobby",
            prototype=0.75,
            observation_values=(0.74, 0.75, 0.76),
            observation_count=3,
            spread=compute_spread([0.74, 0.75, 0.76]),
            guess_count=2,
            correct_count=2,
            incorrect_count=0,
            first_seen_at=ts,
            last_seen_at=ts,
        )
        d = model.to_dict()
        restored = LocationModel.from_dict(d)
        self.assertEqual(model.location_id, restored.location_id)
        self.assertEqual(model.label, restored.label)
        self.assertAlmostEqual(model.prototype, restored.prototype)
        self.assertEqual(list(model.observation_values), list(restored.observation_values))
        self.assertAlmostEqual(model.spread, restored.spread)
        self.assertEqual(model.observation_count, restored.observation_count)

    def test_to_dict_observation_values_is_list(self) -> None:
        ts = utc_now_iso()
        model = LocationModel(
            location_id="loc-a",
            label="x",
            prototype=0.5,
            observation_values=(0.5,),
            observation_count=1,
            spread=0.0,
            guess_count=0,
            correct_count=0,
            incorrect_count=0,
            first_seen_at=ts,
            last_seen_at=ts,
        )
        d = model.to_dict()
        self.assertIsInstance(d["observation_values"], list)


class WithMergedObservationTests(unittest.TestCase):
    def test_merge_two_observations(self) -> None:
        ts = utc_now_iso()
        model = LocationModel(
            location_id="loc-m",
            label="kitchen",
            prototype=0.25,
            observation_values=(0.25,),
            observation_count=1,
            spread=0.0,
            guess_count=0,
            correct_count=0,
            incorrect_count=0,
            first_seen_at=ts,
            last_seen_at=ts,
        )
        merged = model.with_merged_observation(0.26)
        self.assertAlmostEqual(merged.prototype, 0.255)
        self.assertEqual(merged.observation_count, 2)
        self.assertEqual(len(merged.observation_values), 2)
        self.assertGreater(merged.spread, 0.0)

    def test_merge_five_observations(self) -> None:
        ts = utc_now_iso()
        model = LocationModel(
            location_id="loc-m",
            label="kitchen",
            prototype=0.25,
            observation_values=(0.25,),
            observation_count=1,
            spread=0.0,
            guess_count=0,
            correct_count=0,
            incorrect_count=0,
            first_seen_at=ts,
            last_seen_at=ts,
        )
        values = [0.253, 0.248, 0.251, 0.249]
        for v in values:
            model = model.with_merged_observation(v)
        all_vals = [0.25, 0.253, 0.248, 0.251, 0.249]
        expected_mean = sum(all_vals) / len(all_vals)
        expected_spread = compute_spread(all_vals)
        self.assertAlmostEqual(model.prototype, expected_mean)
        self.assertAlmostEqual(model.spread, expected_spread)
        self.assertEqual(model.observation_count, 5)

    def test_merge_ten_observations_converges(self) -> None:
        ts = utc_now_iso()
        model = LocationModel(
            location_id="loc-m",
            label="kitchen",
            prototype=0.25,
            observation_values=(0.25,),
            observation_count=1,
            spread=0.0,
            guess_count=0,
            correct_count=0,
            incorrect_count=0,
            first_seen_at=ts,
            last_seen_at=ts,
        )
        # Merge 9 more values around 0.25 with small noise.
        extras = [0.251, 0.249, 0.252, 0.248, 0.250, 0.253, 0.247, 0.251, 0.250]
        for v in extras:
            model = model.with_merged_observation(v)
        self.assertEqual(model.observation_count, 10)
        # Prototype should be close to 0.25.
        self.assertAlmostEqual(model.prototype, 0.25, places=2)
        # Spread should be small.
        self.assertLess(model.spread, 0.005)

    def test_merge_preserves_immutability(self) -> None:
        ts = utc_now_iso()
        model = LocationModel(
            location_id="loc-m",
            label="kitchen",
            prototype=0.25,
            observation_values=(0.25,),
            observation_count=1,
            spread=0.0,
            guess_count=0,
            correct_count=0,
            incorrect_count=0,
            first_seen_at=ts,
            last_seen_at=ts,
        )
        merged = model.with_merged_observation(0.26)
        # Original should be unchanged.
        self.assertAlmostEqual(model.prototype, 0.25)
        self.assertEqual(model.observation_count, 1)
        self.assertNotEqual(model.prototype, merged.prototype)


class FromRecordTests(unittest.TestCase):
    def test_converts_record_to_model(self) -> None:
        ts = utc_now_iso()
        record = LocationRecord(
            location_id="loc-old",
            observation_key="0.250000",
            observation_value=0.25,
            label="kitchen",
            observation_count=3,
            guess_count=2,
            correct_count=1,
            incorrect_count=1,
            first_seen_at=ts,
            last_seen_at=ts,
        )
        model = LocationModel.from_record(record)
        self.assertEqual(model.location_id, "loc-old")
        self.assertEqual(model.label, "kitchen")
        self.assertAlmostEqual(model.prototype, 0.25)
        self.assertEqual(model.observation_values, (0.25,))
        self.assertAlmostEqual(model.spread, 0.0)
        self.assertEqual(model.observation_count, 3)
        self.assertEqual(model.guess_count, 2)
        self.assertEqual(model.correct_count, 1)
        self.assertEqual(model.incorrect_count, 1)


if __name__ == "__main__":
    unittest.main()
