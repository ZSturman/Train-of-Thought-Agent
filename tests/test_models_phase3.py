from __future__ import annotations

import unittest

from location_agent.models import (
    LabelNode,
    LocationModel,
    LocationRecord,
    RenameRecord,
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
        values = [2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]
        self.assertAlmostEqual(compute_spread(values), 2.0)

    def test_two_values(self) -> None:
        self.assertAlmostEqual(compute_spread([0.2, 0.4]), 0.1)


class LabelNodeTests(unittest.TestCase):
    def test_serialization_round_trip(self) -> None:
        ts = utc_now_iso()
        node = LabelNode(
            label_id="label-xyz",
            canonical_name="Kitchen",
            aliases=("galley", "prep area"),
            rename_history=(
                RenameRecord(
                    old_name="pantry",
                    new_name="Kitchen",
                    renamed_at=ts,
                ),
            ),
            created_at=ts,
            updated_at=ts,
        )

        restored = LabelNode.from_dict(node.to_dict())

        self.assertEqual(node.label_id, restored.label_id)
        self.assertEqual(node.canonical_name, restored.canonical_name)
        self.assertEqual(node.aliases, restored.aliases)
        self.assertEqual(node.rename_history[0].old_name, restored.rename_history[0].old_name)

    def test_with_alias_appends_new_alias(self) -> None:
        ts = utc_now_iso()
        node = LabelNode(
            label_id="label-1",
            canonical_name="kitchen",
            aliases=(),
            rename_history=(),
            created_at=ts,
            updated_at=ts,
        )

        updated = node.with_alias("galley")

        self.assertEqual(("galley",), updated.aliases)
        self.assertEqual("kitchen", updated.canonical_name)

    def test_with_alias_ignores_duplicate_alias(self) -> None:
        ts = utc_now_iso()
        node = LabelNode(
            label_id="label-1",
            canonical_name="kitchen",
            aliases=("galley",),
            rename_history=(),
            created_at=ts,
            updated_at=ts,
        )

        updated = node.with_alias("Galley")

        self.assertEqual(("galley",), updated.aliases)

    def test_with_renamed_canonical_preserves_old_name_as_alias(self) -> None:
        ts = utc_now_iso()
        node = LabelNode(
            label_id="label-1",
            canonical_name="kitchen",
            aliases=("galley",),
            rename_history=(),
            created_at=ts,
            updated_at=ts,
        )

        updated = node.with_renamed_canonical("break room")

        self.assertEqual("break room", updated.canonical_name)
        self.assertIn("kitchen", updated.aliases)
        self.assertIn("galley", updated.aliases)
        self.assertEqual(1, len(updated.rename_history))
        self.assertEqual("kitchen", updated.rename_history[0].old_name)

    def test_with_renamed_canonical_promotes_existing_alias(self) -> None:
        ts = utc_now_iso()
        node = LabelNode(
            label_id="label-1",
            canonical_name="kitchen",
            aliases=("galley", "prep area"),
            rename_history=(),
            created_at=ts,
            updated_at=ts,
        )

        updated = node.with_renamed_canonical("galley")

        self.assertEqual("galley", updated.canonical_name)
        self.assertIn("kitchen", updated.aliases)
        self.assertNotIn("galley", updated.aliases)


class LocationModelCreationTests(unittest.TestCase):
    def test_single_observation_model(self) -> None:
        ts = utc_now_iso()
        model = LocationModel(
            location_id="loc-abc",
            label_id="label-kitchen",
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
        self.assertEqual("label-kitchen", model.label_id)

    def test_serialization_round_trip(self) -> None:
        ts = utc_now_iso()
        model = LocationModel(
            location_id="loc-xyz",
            label_id="label-lobby",
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

        restored = LocationModel.from_dict(model.to_dict())

        self.assertEqual(model.location_id, restored.location_id)
        self.assertEqual(model.label_id, restored.label_id)
        self.assertAlmostEqual(model.prototype, restored.prototype)
        self.assertEqual(model.observation_values, restored.observation_values)
        self.assertAlmostEqual(model.spread, restored.spread)
        self.assertEqual(model.observation_count, restored.observation_count)

    def test_to_dict_observation_values_is_list(self) -> None:
        ts = utc_now_iso()
        model = LocationModel(
            location_id="loc-a",
            label_id="label-a",
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

        payload = model.to_dict()

        self.assertIsInstance(payload["observation_values"], list)
        self.assertEqual("label-a", payload["label_id"])


class WithMergedObservationTests(unittest.TestCase):
    def test_merge_two_observations(self) -> None:
        ts = utc_now_iso()
        model = LocationModel(
            location_id="loc-m",
            label_id="label-kitchen",
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
            label_id="label-kitchen",
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
        for value in values:
            model = model.with_merged_observation(value)

        all_values = [0.25, 0.253, 0.248, 0.251, 0.249]
        self.assertAlmostEqual(model.prototype, sum(all_values) / len(all_values))
        self.assertAlmostEqual(model.spread, compute_spread(all_values))
        self.assertEqual(model.observation_count, 5)

    def test_merge_ten_observations_converges(self) -> None:
        ts = utc_now_iso()
        model = LocationModel(
            location_id="loc-m",
            label_id="label-kitchen",
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
        extras = [0.251, 0.249, 0.252, 0.248, 0.250, 0.253, 0.247, 0.251, 0.250]
        for value in extras:
            model = model.with_merged_observation(value)

        self.assertEqual(model.observation_count, 10)
        self.assertAlmostEqual(model.prototype, 0.25, places=2)
        self.assertLess(model.spread, 0.005)

    def test_merge_preserves_immutability(self) -> None:
        ts = utc_now_iso()
        model = LocationModel(
            location_id="loc-m",
            label_id="label-kitchen",
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

        model = LocationModel.from_record(record, label_id="label-kitchen")

        self.assertEqual("loc-old", model.location_id)
        self.assertEqual("label-kitchen", model.label_id)
        self.assertAlmostEqual(model.prototype, 0.25)
        self.assertEqual((0.25,), model.observation_values)
        self.assertAlmostEqual(0.0, model.spread)
        self.assertEqual(3, model.observation_count)
        self.assertEqual(2, model.guess_count)
        self.assertEqual(1, model.correct_count)
        self.assertEqual(1, model.incorrect_count)


if __name__ == "__main__":
    unittest.main()
