from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from location_agent.memory import LabelConflictError, MemoryStore
from location_agent.models import NormalizedObservation, SCHEMA_VERSION, SensorObservation


class MemoryStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.memory_path = Path(self.temporary_directory.name) / "location_memory.json"

    def test_blank_memory_file_bootstraps(self) -> None:
        self.memory_path.write_text("", encoding="utf-8")
        store = MemoryStore(self.memory_path)

        self.assertEqual({}, store.data["location_models"])
        self.assertEqual({}, store.data["label_nodes"])
        self.assertEqual(0.6, store.guess_threshold)
        self.assertEqual({}, store.data["graph_edges"])
        self.assertEqual({}, store.data["sensor_bindings"])

    def test_learn_and_reload_persists_model_and_label_node(self) -> None:
        store = MemoryStore(self.memory_path)
        observation = NormalizedObservation.parse("0.25")

        _, learned = store.learn_location(observation, "kitchen")
        reloaded = MemoryStore(self.memory_path)
        recalled = reloaded.lookup_by_id(learned.location_id)
        snapshot = reloaded.snapshot_location(recalled.location_id)

        self.assertIsNotNone(recalled)
        self.assertEqual(learned.location_id, recalled.location_id)
        self.assertEqual("kitchen", snapshot["canonical_name"])
        self.assertEqual([], snapshot["aliases"])
        self.assertAlmostEqual(recalled.prototype, 0.25)
        self.assertEqual(1, recalled.observation_count)
        self.assertEqual(1, len(reloaded.data["label_nodes"]))
        self.assertEqual("user", snapshot["provenance_source"])

    def test_reinforce_named_location_reuses_existing_label(self) -> None:
        store = MemoryStore(self.memory_path)
        store.learn_location(NormalizedObservation.parse("0.10"), "Point one")
        store.reinforce_named_location(NormalizedObservation.parse("0.15"), "Point one")

        old_model, updated = store.reinforce_named_location(
            NormalizedObservation.parse("0.20"),
            "Point one",
        )

        self.assertEqual(old_model.location_id, updated.location_id)
        self.assertEqual(3, updated.observation_count)
        self.assertAlmostEqual((0.10 + 0.15 + 0.20) / 3, updated.prototype)

    def test_find_nearest_after_learn(self) -> None:
        store = MemoryStore(self.memory_path)
        store.learn_location(NormalizedObservation.parse("0.25"), "hallway")

        model, confidence = store.find_nearest(NormalizedObservation.parse("0.250000"))
        snapshot = store.snapshot_location(model)

        self.assertIsNotNone(model)
        self.assertEqual("hallway", snapshot["canonical_name"])
        self.assertAlmostEqual(confidence, 1.0)

    def test_lookup_by_label_name_resolves_alias(self) -> None:
        store = MemoryStore(self.memory_path)
        store.learn_location(NormalizedObservation.parse("0.25"), "kitchen")
        store.add_alias("kitchen", "galley")

        resolved = store.lookup_by_label_name("Galley")

        self.assertIsNotNone(resolved)
        model, label = resolved
        self.assertEqual(label.label_id, model.label_id)
        self.assertEqual("kitchen", label.canonical_name)

    def test_rename_label_preserves_old_name_as_alias(self) -> None:
        store = MemoryStore(self.memory_path)
        _, model = store.learn_location(NormalizedObservation.parse("0.25"), "kitchen")

        old_snapshot, new_snapshot = store.rename_label("kitchen", "break room")

        self.assertEqual("kitchen", old_snapshot["canonical_name"])
        self.assertEqual("break room", new_snapshot["canonical_name"])
        self.assertIn("kitchen", new_snapshot["aliases"])
        self.assertEqual(1, len(new_snapshot["rename_history"]))
        self.assertEqual(model.location_id, new_snapshot["location_id"])

    def test_add_alias_updates_snapshot(self) -> None:
        store = MemoryStore(self.memory_path)
        store.learn_location(NormalizedObservation.parse("0.25"), "kitchen")

        old_snapshot, new_snapshot = store.add_alias("kitchen", "galley")

        self.assertEqual([], old_snapshot["aliases"])
        self.assertEqual(["galley"], new_snapshot["aliases"])
        self.assertEqual("kitchen", new_snapshot["canonical_name"])

    def test_duplicate_label_names_are_rejected(self) -> None:
        store = MemoryStore(self.memory_path)
        store.learn_location(NormalizedObservation.parse("0.25"), "kitchen")
        store.learn_location(NormalizedObservation.parse("0.90"), "lobby")

        with self.assertRaises(LabelConflictError):
            store.learn_location(NormalizedObservation.parse("0.75"), "Kitchen")

        with self.assertRaises(LabelConflictError):
            store.add_alias("kitchen", "Lobby")

        with self.assertRaises(LabelConflictError):
            store.rename_label("kitchen", "lobby")

    def test_create_location_supports_sensor_first_learning(self) -> None:
        store = MemoryStore(self.memory_path)

        _, created = store.create_location(
            "camera room",
            location_provenance_source="sensor",
            location_provenance_detail="sensor_path",
            label_provenance_source="user",
            label_provenance_detail="sensor_label",
        )
        snapshot = store.snapshot_location(created.location_id)

        self.assertIsNone(snapshot["prototype"])
        self.assertEqual(0, snapshot["observation_count"])
        self.assertEqual("sensor", snapshot["provenance_source"])


class SchemaMigrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.memory_path = Path(self.temporary_directory.name) / "location_memory.json"

    def test_v3_to_v4_migration(self) -> None:
        v3_payload = {
            "schema_version": 3,
            "created_at": "2026-03-26T08:47:07+00:00",
            "updated_at": "2026-03-28T00:00:00+00:00",
            "confidence_policy": {
                "kind": "distance",
                "tolerance": 0.05,
                "guess_threshold": 0.6,
                "normalization_decimals": 6,
                "outlier_factor": 3.0,
            },
            "location_models": {
                "loc-oldkitchen": {
                    "location_id": "loc-oldkitchen",
                    "label": "kitchen",
                    "prototype": 0.25,
                    "observation_values": [0.25, 0.251],
                    "observation_count": 2,
                    "spread": 0.0005,
                    "guess_count": 1,
                    "correct_count": 1,
                    "incorrect_count": 0,
                    "first_seen_at": "2026-03-26T08:47:07+00:00",
                    "last_seen_at": "2026-03-28T00:00:00+00:00",
                },
            },
        }
        self.memory_path.write_text(json.dumps(v3_payload), encoding="utf-8")

        store = MemoryStore(self.memory_path)
        models = store.inspect_models()

        self.assertEqual(SCHEMA_VERSION, store.data["schema_version"])
        self.assertIn("label_nodes", store.data)
        self.assertEqual(1, len(store.data["label_nodes"]))
        self.assertEqual("kitchen", models[0]["canonical_name"])
        self.assertEqual([], models[0]["aliases"])

    def test_v2_to_v4_migration(self) -> None:
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
        labels = {model["canonical_name"] for model in store.inspect_models()}

        self.assertEqual(SCHEMA_VERSION, store.data["schema_version"])
        self.assertNotIn("locations_by_observation", store.data)
        self.assertEqual({"kitchen", "lobby"}, labels)

    def test_v1_to_v4_migration(self) -> None:
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
        models = store.inspect_models()

        self.assertEqual(SCHEMA_VERSION, store.data["schema_version"])
        self.assertEqual(1, len(models))
        self.assertEqual("office", models[0]["canonical_name"])

    def test_duplicate_v3_labels_are_disambiguated_on_migration(self) -> None:
        v3_payload = {
            "schema_version": 3,
            "created_at": "2026-03-26T08:47:07+00:00",
            "updated_at": "2026-03-28T00:00:00+00:00",
            "confidence_policy": {
                "kind": "distance",
                "tolerance": 0.05,
                "guess_threshold": 0.6,
                "normalization_decimals": 6,
                "outlier_factor": 3.0,
            },
            "location_models": {
                "loc-one": {
                    "location_id": "loc-one",
                    "label": "kitchen",
                    "prototype": 0.25,
                    "observation_values": [0.25],
                    "observation_count": 1,
                    "spread": 0.0,
                    "guess_count": 0,
                    "correct_count": 0,
                    "incorrect_count": 0,
                    "first_seen_at": "2026-03-26T08:47:07+00:00",
                    "last_seen_at": "2026-03-26T08:47:07+00:00",
                },
                "loc-two": {
                    "location_id": "loc-two",
                    "label": "kitchen",
                    "prototype": 0.75,
                    "observation_values": [0.75],
                    "observation_count": 1,
                    "spread": 0.0,
                    "guess_count": 0,
                    "correct_count": 0,
                    "incorrect_count": 0,
                    "first_seen_at": "2026-03-26T08:47:07+00:00",
                    "last_seen_at": "2026-03-26T08:47:07+00:00",
                },
            },
        }
        self.memory_path.write_text(json.dumps(v3_payload), encoding="utf-8")

        store = MemoryStore(self.memory_path)
        labels = sorted(model["canonical_name"] for model in store.inspect_models())

        self.assertEqual(["kitchen", "kitchen (2)"], labels)

    def test_v4_to_v5_migration_adds_graph_and_provenance_scaffolding(self) -> None:
        v4_payload = {
            "schema_version": 4,
            "created_at": "2026-03-28T00:00:00+00:00",
            "updated_at": "2026-03-28T00:00:00+00:00",
            "confidence_policy": {
                "kind": "distance",
                "tolerance": 0.05,
                "guess_threshold": 0.6,
                "normalization_decimals": 6,
                "outlier_factor": 3.0,
            },
            "location_models": {
                "loc-room": {
                    "location_id": "loc-room",
                    "label_id": "label-room",
                    "prototype": 0.4,
                    "observation_values": [0.4],
                    "observation_count": 1,
                    "spread": 0.0,
                    "guess_count": 0,
                    "correct_count": 0,
                    "incorrect_count": 0,
                    "first_seen_at": "2026-03-28T00:00:00+00:00",
                    "last_seen_at": "2026-03-28T00:00:00+00:00",
                }
            },
            "label_nodes": {
                "label-room": {
                    "label_id": "label-room",
                    "canonical_name": "room",
                    "aliases": [],
                    "rename_history": [],
                    "created_at": "2026-03-28T00:00:00+00:00",
                    "updated_at": "2026-03-28T00:00:00+00:00",
                }
            },
        }
        self.memory_path.write_text(json.dumps(v4_payload), encoding="utf-8")

        store = MemoryStore(self.memory_path)

        self.assertEqual(SCHEMA_VERSION, store.data["schema_version"])
        self.assertIn("graph_edges", store.data)
        self.assertIn("sensor_bindings", store.data)
        self.assertIn("evidence_records", store.data)
        model = store.lookup_by_id("loc-room")
        self.assertEqual("user", model.provenance_source)


class InspectModelsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.memory_path = Path(self.temporary_directory.name) / "location_memory.json"

    def test_empty_store_returns_empty_list(self) -> None:
        store = MemoryStore(self.memory_path)
        self.assertEqual([], store.inspect_models())

    def test_inspect_returns_label_aware_fields(self) -> None:
        store = MemoryStore(self.memory_path)
        store.learn_location(NormalizedObservation.parse("0.25"), "kitchen")
        store.add_alias("kitchen", "galley")

        models = store.inspect_models()

        self.assertEqual(1, len(models))
        model = models[0]
        self.assertIn("location_id", model)
        self.assertIn("label_id", model)
        self.assertIn("label", model)
        self.assertIn("canonical_name", model)
        self.assertIn("aliases", model)
        self.assertIn("rename_history", model)
        self.assertIn("active_context", model)
        self.assertIn("concepts", model)
        self.assertIn("provenance_source", model)
        self.assertEqual(["galley"], model["aliases"])


class LocationGraphTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.memory_path = Path(self.temporary_directory.name) / "location_memory.json"

    def test_nested_context_keeps_parent_active(self) -> None:
        store = MemoryStore(self.memory_path)
        store.learn_location(NormalizedObservation.parse("0.10"), "house")
        store.learn_location(NormalizedObservation.parse("0.20"), "bedroom")
        store.learn_location(NormalizedObservation.parse("0.30"), "living room")

        store.link_locations("house", "bedroom")
        store.link_locations("house", "living room")

        self.assertEqual(["bedroom", "house"], store.active_context_names("bedroom"))
        self.assertEqual(["living room", "house"], store.active_context_names("living room"))

    def test_attach_concept_creates_node_and_link(self) -> None:
        store = MemoryStore(self.memory_path)
        store.learn_location(NormalizedObservation.parse("0.20"), "bedroom")

        concept, edge = store.attach_concept("bedroom", "morning")
        snapshot = store.snapshot_location("bedroom")

        self.assertEqual("morning", concept.concept_name)
        self.assertEqual("context_label", edge.relation_kind)
        self.assertIn("morning", snapshot["concepts"])


class SensorBindingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.memory_path = Path(self.temporary_directory.name) / "location_memory.json"
        self.sensor_path = Path(self.temporary_directory.name) / "room.jpg"
        self.sensor_path.write_bytes(b"fake-image-bytes")

    def test_bind_sensor_observation_persists_and_recognizes_fingerprint(self) -> None:
        store = MemoryStore(self.memory_path)
        sensor_observation = SensorObservation.from_path(str(self.sensor_path))

        old_snapshot, new_snapshot, created = store.bind_sensor_observation(
            sensor_observation,
            "bedroom",
        )
        reloaded = MemoryStore(self.memory_path)
        recognized = reloaded.lookup_sensor_binding(sensor_observation.fingerprint)

        self.assertIsNone(old_snapshot)
        self.assertTrue(created)
        self.assertEqual("bedroom", new_snapshot["canonical_name"])
        self.assertIsNotNone(recognized)
        _, model, label = recognized
        self.assertEqual(model.location_id, new_snapshot["location_id"])
        self.assertEqual("bedroom", label.canonical_name)

    def test_evidence_records_only_store_user_or_sensor_sources(self) -> None:
        store = MemoryStore(self.memory_path)
        store.learn_location(NormalizedObservation.parse("0.25"), "bedroom")
        sensor_observation = SensorObservation.from_path(str(self.sensor_path))
        store.bind_sensor_observation(sensor_observation, "bedroom")
        store.attach_concept("bedroom", "night time")

        sources = {record["source_kind"] for record in store.data["evidence_records"].values()}

        self.assertTrue(sources <= {"user", "sensor"})
        self.assertNotIn("llm", sources)


class ResetMemoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.memory_path = Path(self.temporary_directory.name) / "location_memory.json"

    def test_reset_clears_all_models_and_labels(self) -> None:
        store = MemoryStore(self.memory_path)
        store.learn_location(NormalizedObservation.parse("0.25"), "kitchen")
        store.learn_location(NormalizedObservation.parse("0.90"), "lobby")

        count = store.reset_memory()

        self.assertEqual(2, count)
        self.assertEqual([], store.inspect_models())
        self.assertEqual({}, store.data["label_nodes"])
        self.assertEqual({}, store.data["graph_edges"])
        self.assertEqual({}, store.data["sensor_bindings"])

    def test_reset_returns_zero_on_empty_store(self) -> None:
        store = MemoryStore(self.memory_path)
        count = store.reset_memory()
        self.assertEqual(0, count)
        self.assertEqual([], store.inspect_models())
        self.assertEqual({}, store.data["label_nodes"])

    def test_reset_persists_across_reload(self) -> None:
        store = MemoryStore(self.memory_path)
        store.learn_location(NormalizedObservation.parse("0.50"), "hallway")
        store.reset_memory()

        reloaded = MemoryStore(self.memory_path)
        self.assertEqual([], reloaded.inspect_models())
        self.assertEqual(SCHEMA_VERSION, reloaded.data["schema_version"])

    def test_reset_preserves_schema_version(self) -> None:
        store = MemoryStore(self.memory_path)
        store.learn_location(NormalizedObservation.parse("0.25"), "kitchen")
        store.reset_memory()
        self.assertEqual(SCHEMA_VERSION, store.data["schema_version"])
        self.assertIn("confidence_policy", store.data)


if __name__ == "__main__":
    unittest.main()
