from __future__ import annotations

import json
import re
import tempfile
import unittest
from collections import defaultdict
from pathlib import Path

from location_agent.logging import EventLogger
from location_agent.memory import MemoryStore
from location_agent.models import SensorObservation
from location_agent.session import SessionController

REPO_ROOT = Path(__file__).resolve().parents[1]
MEDIA_ROOT = REPO_ROOT / "media"
CATALOG_PATH = MEDIA_ROOT / "catalog.json"
SCENARIO_ROOT = MEDIA_ROOT / "scenarios"
MEDIA_PLAN_PATH = REPO_ROOT / "MEDIA_PLAN.md"
ROADMAP_PATH = REPO_ROOT / "PROJECT_ROADMAP.md"

SUPPORTED_MEDIA_MODALITIES = {"image", "video", "audio", "text", "binary"}


class InputFeeder:
    def __init__(self, values: list[str]):
        self.values = list(values)

    def __call__(self, prompt: str) -> str:
        del prompt
        if not self.values:
            raise EOFError
        return self.values.pop(0)


class OutputCollector:
    def __init__(self) -> None:
        self.lines: list[str] = []

    def __call__(self, message: str) -> None:
        self.lines.append(message)


def _load_catalog() -> list[dict[str, object]]:
    with CATALOG_PATH.open("r", encoding="utf-8") as handle:
        return list(json.load(handle)["assets"])


def _load_scenarios() -> list[dict[str, object]]:
    scenarios: list[dict[str, object]] = []
    for path in sorted(SCENARIO_ROOT.glob("*.json")):
        with path.open("r", encoding="utf-8") as handle:
            scenarios.append(json.load(handle))
    return scenarios


def _phase_section(document: str, phase_number: int) -> str:
    match = re.search(
        rf"## Phase {phase_number} - .*?(?=\n## Phase \d+ - |\n---|\Z)",
        document,
        flags=re.DOTALL,
    )
    if match is None:
        raise AssertionError(f"missing phase section for phase {phase_number}")
    return match.group(0)


class MediaManifestTests(unittest.TestCase):
    def test_catalog_entries_have_required_fields_and_real_files(self) -> None:
        required_fields = {
            "asset_id",
            "phase",
            "location_label",
            "scene_name",
            "modality",
            "path",
            "source_kind",
            "license",
            "used_for",
            "notes",
        }

        assets = _load_catalog()
        self.assertGreaterEqual(len(assets), 7)

        for entry in assets:
            self.assertTrue(required_fields <= set(entry))
            self.assertIn(entry["modality"], SUPPORTED_MEDIA_MODALITIES)
            self.assertIsInstance(entry["phase"], int)
            self.assertIsInstance(entry["asset_id"], str)
            self.assertIsInstance(entry["scene_name"], str)
            self.assertIsInstance(entry["path"], str)
            self.assertIsInstance(entry["source_kind"], str)
            self.assertIsInstance(entry["license"], str)
            self.assertIsInstance(entry["used_for"], list)
            self.assertIsInstance(entry["notes"], str)
            self.assertTrue((REPO_ROOT / str(entry["path"])).is_file(), entry["path"])

    def test_catalog_assets_are_referenced_by_phase_aligned_scenarios(self) -> None:
        assets = _load_catalog()
        scenario_phases_by_asset: dict[str, set[int]] = defaultdict(set)

        for scenario in _load_scenarios():
            phase = int(scenario["phase"])
            self.assertIsInstance(scenario["scenario_id"], str)
            self.assertIsInstance(scenario["goal"], str)
            self.assertIsInstance(scenario["steps"], list)
            self.assertTrue(scenario["steps"])
            for step in scenario["steps"]:
                self.assertIsInstance(step["asset_ids"], list)
                self.assertTrue(step["asset_ids"])
                self.assertIsInstance(step["expected_outcome"], str)
                for asset_id in step["asset_ids"]:
                    scenario_phases_by_asset[str(asset_id)].add(phase)

        for entry in assets:
            phases = scenario_phases_by_asset[str(entry["asset_id"])]
            self.assertTrue(phases, f"asset {entry['asset_id']} is not referenced by any scenario")
            self.assertIn(int(entry["phase"]), phases)


class MediaDocumentationTests(unittest.TestCase):
    def test_media_plan_and_roadmap_define_pack_and_scenario_for_phases_4_to_28(self) -> None:
        media_plan = MEDIA_PLAN_PATH.read_text(encoding="utf-8")
        roadmap = ROADMAP_PATH.read_text(encoding="utf-8")

        self.assertIn("ObservationBundle", media_plan)
        self.assertIn("ObservationBundle", roadmap)
        self.assertIn("ExperienceFrame", media_plan)
        self.assertIn("ExperienceFrame", roadmap)
        self.assertIn("MemoryUnit", media_plan)
        self.assertIn("MemoryUnit", roadmap)
        self.assertIn("blue streak across top", media_plan)
        self.assertIn("blue streak across top", roadmap)
        self.assertIn("green streak across bottom", media_plan)
        self.assertIn("green streak across bottom", roadmap)
        self.assertIn("park", media_plan)
        self.assertIn("yard", roadmap)
        self.assertIn("temporary", media_plan.lower())
        self.assertIn("temporary", roadmap.lower())

        for phase in range(4, 29):
            media_plan_section = _phase_section(media_plan, phase)
            self.assertIn("- Required pack:", media_plan_section)
            self.assertIn("- Validation scenario:", media_plan_section)
            self.assertIn("- Bridge to next sensing step:", media_plan_section)

            roadmap_section = _phase_section(roadmap, phase)
            self.assertIn("- Phase media:", roadmap_section)
            self.assertIn("- Validation scenario:", roadmap_section)
            self.assertIn("- Next sensing bridge:", roadmap_section)

        self.assertIn("salience", _phase_section(roadmap, 9).lower())
        self.assertIn("hypoth", _phase_section(roadmap, 10).lower())
        self.assertIn("memoryunit", _phase_section(roadmap, 13).replace("`", "").lower())
        self.assertIn("attention", _phase_section(roadmap, 16).lower())
        self.assertIn("threshold", _phase_section(roadmap, 17).lower())
        self.assertIn("resurfacing", _phase_section(roadmap, 19).lower())
        self.assertIn("reconsolidation", _phase_section(roadmap, 21).lower())
        self.assertIn("nonhuman", _phase_section(roadmap, 24).replace("-", "").lower())
        self.assertIn("pose", _phase_section(roadmap, 25).lower())
        self.assertIn("sensor_origin", _phase_section(media_plan, 25))


class Phase4MediaSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        runtime_path = Path(self.temporary_directory.name)
        self.memory_path = runtime_path / "location_memory.json"
        self.event_log_path = runtime_path / "agent_events.jsonl"
        self.asset_paths = {
            entry["asset_id"]: (REPO_ROOT / str(entry["path"])).resolve()
            for entry in _load_catalog()
        }

    def _run(self, values: list[str]) -> OutputCollector:
        feeder = InputFeeder(values)
        output = OutputCollector()
        controller = SessionController(
            store=MemoryStore(self.memory_path),
            event_logger=EventLogger(self.event_log_path),
            input_func=feeder,
            output_func=output,
            session_id="media-smoke",
            quiet=True,
        )
        controller.run()
        return output

    def test_phase4_committed_fixtures_cover_unknown_known_and_unknown_again(self) -> None:
        break_room_path = self.asset_paths["phase04_break_room_scene"]
        unknown_path = self.asset_paths["phase04_unknown_scene"]

        output = self._run(
            [
                f"sense {break_room_path}",
                "break room",
                f"sense {break_room_path}",
                "yes",
                f"sense {unknown_path}",
                "storage closet",
                "quit",
            ]
        )

        combined = "\n".join(output.lines)
        self.assertGreaterEqual(combined.count("sensor: new image"), 2)
        self.assertIn("sensor: recognized image", combined)
        self.assertIn("guess: break room (confidence=1.00)", combined)

        reloaded = MemoryStore(self.memory_path)
        self.assertIsNotNone(
            reloaded.lookup_sensor_binding(SensorObservation.from_path(str(break_room_path)).fingerprint)
        )
        self.assertIsNotNone(
            reloaded.lookup_sensor_binding(SensorObservation.from_path(str(unknown_path)).fingerprint)
        )


class Phase5MediaManifestTests(unittest.TestCase):
    def test_phase5_nested_context_scenario_reuses_registered_room_assets_and_house_fixture(self) -> None:
        assets = {entry["asset_id"]: entry for entry in _load_catalog()}
        scenario = next(
            item for item in _load_scenarios() if item["scenario_id"] == "phase_05_nested_context_walk"
        )

        referenced_asset_ids = {
            str(asset_id)
            for step in scenario["steps"]
            for asset_id in step["asset_ids"]
        }

        self.assertEqual(5, int(scenario["phase"]))
        self.assertIn("phase05_house_scene", referenced_asset_ids)
        self.assertIn("phase04_bedroom_scene", referenced_asset_ids)
        self.assertIn("phase04_living_room_scene", referenced_asset_ids)
        self.assertTrue((REPO_ROOT / str(assets["phase05_house_scene"]["path"])).is_file())
        for asset_id in referenced_asset_ids:
            self.assertIn(asset_id, assets)
