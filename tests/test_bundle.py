from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from location_agent.memory import MemoryStore
from location_agent.models import (
    ImageAdapter,
    ObservationBundle,
    RegionDescriptor,
    SCHEMA_VERSION,
    SensorAdapter,
    SensorObservation,
    SensorObservationError,
    utc_now_iso,
)


class ObservationBundleFieldTests(unittest.TestCase):
    """Verify ObservationBundle validation and serialization."""

    def test_valid_bundle_round_trip(self) -> None:
        region = RegionDescriptor(
            region_id="region-001",
            label="top-half",
            geometry={"x": 0.0, "y": 0.0, "w": 1.0, "h": 0.5},
            salience=0.8,
        )
        bundle = ObservationBundle(
            bundle_id="bundle-abc123",
            timestamp=utc_now_iso(),
            adapter_id="test-adapter-v1",
            modality="image",
            reference_frame="camera-front",
            pose_estimate={"x": 1.0, "y": 2.0, "z": 0.0},
            motion_estimate={"vx": 0.1, "vy": 0.0},
            sensor_origin="/dev/cam0",
            regions=(region,),
            primitive_features=("blue streak across top",),
            concept_candidates=("sky",),
            raw_refs=("/path/to/image.png",),
            provenance="sensor",
        )
        restored = ObservationBundle.from_dict(bundle.to_dict())

        self.assertEqual(bundle.bundle_id, restored.bundle_id)
        self.assertEqual(bundle.adapter_id, restored.adapter_id)
        self.assertEqual(bundle.modality, restored.modality)
        self.assertEqual(bundle.reference_frame, restored.reference_frame)
        self.assertEqual(bundle.pose_estimate, restored.pose_estimate)
        self.assertEqual(bundle.motion_estimate, restored.motion_estimate)
        self.assertEqual(bundle.sensor_origin, restored.sensor_origin)
        self.assertEqual(len(bundle.regions), len(restored.regions))
        self.assertEqual(bundle.regions[0].region_id, restored.regions[0].region_id)
        self.assertEqual(bundle.regions[0].salience, restored.regions[0].salience)
        self.assertEqual(bundle.primitive_features, restored.primitive_features)
        self.assertEqual(bundle.concept_candidates, restored.concept_candidates)
        self.assertEqual(bundle.raw_refs, restored.raw_refs)
        self.assertEqual(bundle.provenance, restored.provenance)

    def test_empty_bundle_id_rejected(self) -> None:
        with self.assertRaises(ValueError):
            ObservationBundle(
                bundle_id="",
                timestamp=utc_now_iso(),
                adapter_id="test",
                modality="image",
            )

    def test_empty_timestamp_rejected(self) -> None:
        with self.assertRaises(ValueError):
            ObservationBundle(
                bundle_id="bundle-001",
                timestamp="",
                adapter_id="test",
                modality="image",
            )

    def test_empty_adapter_id_rejected(self) -> None:
        with self.assertRaises(ValueError):
            ObservationBundle(
                bundle_id="bundle-001",
                timestamp=utc_now_iso(),
                adapter_id="",
                modality="image",
            )

    def test_empty_modality_rejected(self) -> None:
        with self.assertRaises(ValueError):
            ObservationBundle(
                bundle_id="bundle-001",
                timestamp=utc_now_iso(),
                adapter_id="test",
                modality="",
            )

    def test_invalid_provenance_rejected(self) -> None:
        with self.assertRaises(ValueError):
            ObservationBundle(
                bundle_id="bundle-001",
                timestamp=utc_now_iso(),
                adapter_id="test",
                modality="image",
                provenance="llm",
            )

    def test_minimal_bundle_defaults(self) -> None:
        bundle = ObservationBundle(
            bundle_id="bundle-min",
            timestamp=utc_now_iso(),
            adapter_id="test",
            modality="audio",
        )
        self.assertIsNone(bundle.reference_frame)
        self.assertIsNone(bundle.pose_estimate)
        self.assertIsNone(bundle.motion_estimate)
        self.assertIsNone(bundle.sensor_origin)
        self.assertEqual((), bundle.regions)
        self.assertEqual((), bundle.primitive_features)
        self.assertEqual((), bundle.concept_candidates)
        self.assertEqual((), bundle.raw_refs)
        self.assertEqual("sensor", bundle.provenance)

    def test_region_descriptor_round_trip(self) -> None:
        region = RegionDescriptor(
            region_id="r-1",
            label="center-patch",
            geometry={"cx": 0.5, "cy": 0.5, "radius": 0.1},
            salience=0.95,
        )
        restored = RegionDescriptor.from_dict(region.to_dict())
        self.assertEqual(region.region_id, restored.region_id)
        self.assertEqual(region.label, restored.label)
        self.assertEqual(region.geometry, restored.geometry)
        self.assertAlmostEqual(region.salience, restored.salience)


class ImageAdapterTests(unittest.TestCase):
    """Verify ImageAdapter produces valid ObservationBundle from image files."""

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.image_path = Path(self.temporary_directory.name) / "test_scene.png"
        self.image_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)

    def test_adapter_properties(self) -> None:
        adapter = ImageAdapter()
        self.assertEqual("image-adapter-v1", adapter.adapter_id)
        self.assertEqual("image", adapter.modality)

    def test_observe_produces_valid_bundle(self) -> None:
        adapter = ImageAdapter()
        bundle = adapter.observe(str(self.image_path))

        self.assertTrue(bundle.bundle_id.startswith("bundle-"))
        self.assertEqual("image-adapter-v1", bundle.adapter_id)
        self.assertEqual("image", bundle.modality)
        self.assertEqual("sensor", bundle.provenance)
        self.assertEqual(1, len(bundle.raw_refs))
        self.assertEqual(str(self.image_path.resolve()), bundle.raw_refs[0])
        self.assertEqual(str(self.image_path.resolve()), bundle.sensor_origin)

    def test_observe_invalid_path_raises(self) -> None:
        adapter = ImageAdapter()
        with self.assertRaises(SensorObservationError):
            adapter.observe("/nonexistent/file.png")

    def test_fingerprint_from_bundle(self) -> None:
        adapter = ImageAdapter()
        bundle = adapter.observe(str(self.image_path))

        fingerprint = adapter.fingerprint_from_bundle(bundle)
        direct = SensorObservation.from_path(str(self.image_path))

        self.assertIsNotNone(fingerprint)
        self.assertEqual(direct.fingerprint, fingerprint)

    def test_sensor_observation_from_bundle(self) -> None:
        adapter = ImageAdapter()
        bundle = adapter.observe(str(self.image_path))

        sensor_obs = adapter.sensor_observation_from_bundle(bundle)
        self.assertIsNotNone(sensor_obs)
        self.assertEqual(str(self.image_path.resolve()), sensor_obs.resolved_path)
        self.assertEqual("image", sensor_obs.media_kind)

    def test_two_adapters_produce_same_bundle_shape(self) -> None:
        """Two ImageAdapter instances produce the same field set."""
        adapter_a = ImageAdapter()
        adapter_b = ImageAdapter()

        bundle_a = adapter_a.observe(str(self.image_path))
        bundle_b = adapter_b.observe(str(self.image_path))

        dict_a = bundle_a.to_dict()
        dict_b = bundle_b.to_dict()

        # Same keys (shape) even if values differ (bundle_id, timestamp)
        self.assertEqual(set(dict_a.keys()), set(dict_b.keys()))
        self.assertEqual(bundle_a.adapter_id, bundle_b.adapter_id)
        self.assertEqual(bundle_a.modality, bundle_b.modality)
        self.assertEqual(bundle_a.raw_refs, bundle_b.raw_refs)

    def test_adapter_is_sensor_adapter_subclass(self) -> None:
        adapter = ImageAdapter()
        self.assertIsInstance(adapter, SensorAdapter)


class MockAudioAdapter(SensorAdapter):
    """Placeholder adapter to verify two different adapters produce matching bundle shapes."""

    @property
    def adapter_id(self) -> str:
        return "audio-adapter-v1"

    @property
    def modality(self) -> str:
        return "audio"

    def observe(self, raw_input: str) -> ObservationBundle:
        import uuid
        return ObservationBundle(
            bundle_id=f"bundle-{uuid.uuid4().hex[:12]}",
            timestamp=utc_now_iso(),
            adapter_id=self.adapter_id,
            modality=self.modality,
            raw_refs=(raw_input,),
            provenance="sensor",
        )


class CrossAdapterShapeTests(unittest.TestCase):
    """Verify that different adapters produce identical bundle field sets."""

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.image_path = Path(self.temporary_directory.name) / "scene.png"
        self.image_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 64)

    def test_image_and_audio_adapters_share_bundle_keys(self) -> None:
        image_adapter = ImageAdapter()
        audio_adapter = MockAudioAdapter()

        image_bundle = image_adapter.observe(str(self.image_path))
        audio_bundle = audio_adapter.observe("/fake/audio.wav")

        self.assertEqual(
            set(image_bundle.to_dict().keys()),
            set(audio_bundle.to_dict().keys()),
        )

    def test_both_adapters_are_sensor_adapter_subclass(self) -> None:
        self.assertIsInstance(ImageAdapter(), SensorAdapter)
        self.assertIsInstance(MockAudioAdapter(), SensorAdapter)


class BundlePersistenceTests(unittest.TestCase):
    """Verify bundles persist in memory and schema v7 migration works."""

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.memory_path = Path(self.temporary_directory.name) / "location_memory.json"

    def test_schema_version_is_7(self) -> None:
        self.assertEqual(7, SCHEMA_VERSION)

    def test_store_and_retrieve_bundle(self) -> None:
        store = MemoryStore(self.memory_path)
        bundle = ObservationBundle(
            bundle_id="bundle-test001",
            timestamp=utc_now_iso(),
            adapter_id="image-adapter-v1",
            modality="image",
            raw_refs=("/some/path.png",),
            provenance="sensor",
        )
        store.store_bundle(bundle)

        retrieved = store.get_bundle("bundle-test001")
        self.assertIsNotNone(retrieved)
        self.assertEqual(bundle.bundle_id, retrieved.bundle_id)
        self.assertEqual(bundle.adapter_id, retrieved.adapter_id)
        self.assertEqual(bundle.raw_refs, retrieved.raw_refs)

    def test_bundle_persists_across_reload(self) -> None:
        store = MemoryStore(self.memory_path)
        bundle = ObservationBundle(
            bundle_id="bundle-persist",
            timestamp=utc_now_iso(),
            adapter_id="image-adapter-v1",
            modality="image",
            provenance="sensor",
        )
        store.store_bundle(bundle)

        reloaded = MemoryStore(self.memory_path)
        retrieved = reloaded.get_bundle("bundle-persist")
        self.assertIsNotNone(retrieved)
        self.assertEqual("bundle-persist", retrieved.bundle_id)

    def test_get_nonexistent_bundle_returns_none(self) -> None:
        store = MemoryStore(self.memory_path)
        self.assertIsNone(store.get_bundle("bundle-nope"))

    def test_bind_sensor_bundle_stores_both(self) -> None:
        store = MemoryStore(self.memory_path)
        tmp_file = Path(self.temporary_directory.name) / "img.png"
        tmp_file.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)
        adapter = ImageAdapter()
        bundle = adapter.observe(str(tmp_file))
        sensor_obs = adapter.sensor_observation_from_bundle(bundle)

        _, snapshot, created = store.bind_sensor_bundle(bundle, sensor_obs, "test room")

        self.assertTrue(created)
        self.assertEqual("test room", snapshot["canonical_name"])
        # Bundle is stored
        self.assertIsNotNone(store.get_bundle(bundle.bundle_id))
        # Sensor binding is stored
        binding_result = store.lookup_sensor_binding(sensor_obs.fingerprint)
        self.assertIsNotNone(binding_result)

    def test_v6_to_v7_migration(self) -> None:
        """A v6 memory file gains observation_bundles on load."""
        import json
        v6_payload = {
            "schema_version": 6,
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso(),
            "confidence_policy": {
                "kind": "distance",
                "tolerance": 0.05,
                "guess_threshold": 0.6,
                "normalization_decimals": 6,
                "outlier_factor": 3.0,
            },
            "location_models": {},
            "label_nodes": {},
            "concept_nodes": {},
            "graph_edges": {},
            "sensor_bindings": {},
            "evidence_records": {},
        }
        self.memory_path.write_text(json.dumps(v6_payload), encoding="utf-8")

        store = MemoryStore(self.memory_path)
        self.assertEqual(7, store.data["schema_version"])
        self.assertIn("observation_bundles", store.data)
        self.assertEqual({}, store.data["observation_bundles"])

    def test_new_store_has_observation_bundles(self) -> None:
        store = MemoryStore(self.memory_path)
        self.assertIn("observation_bundles", store.data)
        self.assertEqual(7, store.data["schema_version"])


if __name__ == "__main__":
    unittest.main()
