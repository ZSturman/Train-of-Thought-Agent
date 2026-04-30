"""Validate live runtime artifacts against the published JSON Schemas."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import jsonschema

from location_agent import Agent
from location_agent.models import ObservationBundle, RegionDescriptor, utc_now_iso

SCHEMAS_DIR = Path(__file__).resolve().parent.parent / "schemas"


def _load_schema(name: str) -> dict:
    return json.loads((SCHEMAS_DIR / name).read_text(encoding="utf-8"))


class ObservationBundleSchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.schema = _load_schema("observation_bundle.schema.json")

    def test_built_bundle_validates(self) -> None:
        bundle = ObservationBundle(
            bundle_id="b-1",
            timestamp=utc_now_iso(),
            adapter_id="image-adapter-v0",
            modality="image",
            regions=(RegionDescriptor(region_id="r0", salience=0.5),),
            primitive_features=("edge",),
            concept_candidates=(),
            raw_refs=("sha256:abc",),
            provenance="sensor",
        )
        jsonschema.validate(instance=bundle.to_dict(), schema=self.schema)

    def test_missing_required_field_fails(self) -> None:
        payload = {
            "timestamp": "2024-01-01T00:00:00+00:00",
            "adapter_id": "x",
            "modality": "image",
            "regions": [],
            "primitive_features": [],
            "concept_candidates": [],
            "raw_refs": [],
            "provenance": "sensor",
        }
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(instance=payload, schema=self.schema)

    def test_invalid_provenance_fails(self) -> None:
        bundle = ObservationBundle(
            bundle_id="b-2",
            timestamp=utc_now_iso(),
            adapter_id="x",
            modality="image",
            provenance="sensor",
        )
        bad = bundle.to_dict()
        bad["provenance"] = "bogus"
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(instance=bad, schema=self.schema)


class RuntimeMemorySchemaTests(unittest.TestCase):
    def setUp(self) -> None:
        self.schema = _load_schema("runtime_memory.v7.schema.json")

    def test_live_memory_snapshot_validates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            agent = Agent(runtime_dir=Path(tmp))
            agent.learn_scalar(0.4, "kitchen")
            agent.learn_scalar(0.7, "garage")
            persisted = json.loads((Path(tmp) / "location_memory.json").read_text(encoding="utf-8"))
        jsonschema.validate(instance=persisted, schema=self.schema)

    def test_missing_top_level_section_fails(self) -> None:
        bad = {
            "schema_version": 7,
            "confidence_policy": {"guess_threshold": 0.85, "tolerance": 0.05},
            "location_models": {},
            # Intentionally drop label_nodes
            "concept_nodes": {},
            "graph_edges": {},
            "sensor_bindings": {},
            "evidence_records": {},
            "observation_bundles": {},
        }
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.validate(instance=bad, schema=self.schema)


if __name__ == "__main__":
    unittest.main()
