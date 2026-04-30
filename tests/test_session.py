from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from location_agent.logging import EventLogger
from location_agent.memory import MemoryStore
from location_agent.models import SensorObservation
from location_agent.session import SessionController


class InputFeeder:
    def __init__(self, values: list[str]):
        self.values = list(values)
        self.prompts: list[str] = []

    def __call__(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if not self.values:
            raise EOFError
        return self.values.pop(0)


class OutputCollector:
    def __init__(self) -> None:
        self.lines: list[str] = []

    def __call__(self, message: str) -> None:
        self.lines.append(message)


class SessionControllerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        runtime_path = Path(self.temporary_directory.name)
        self.memory_path = runtime_path / "location_memory.json"
        self.event_log_path = runtime_path / "agent_events.jsonl"
        self.sensor_path = runtime_path / "bedroom.jpg"
        self.sensor_path.write_bytes(b"pretend-image")

    def _parse_events(self) -> list[dict[str, object]]:
        with self.event_log_path.open("r", encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]

    def _run(self, values: list[str], *, quiet: bool = True) -> tuple[InputFeeder, OutputCollector]:
        feeder = InputFeeder(values)
        output = OutputCollector()
        controller = SessionController(
            store=MemoryStore(self.memory_path),
            event_logger=EventLogger(self.event_log_path),
            input_func=feeder,
            output_func=output,
            session_id="test-session",
            quiet=quiet,
        )
        controller.run()
        return feeder, output

    def test_unknown_then_known_correct_guess_persists_and_logs(self) -> None:
        _, output = self._run(["0.25", "kitchen", "0.250000", "1", "quit"])

        reloaded = MemoryStore(self.memory_path)
        kitchen = next(
            model for model in reloaded.inspect_models() if model["canonical_name"] == "kitchen"
        )
        self.assertAlmostEqual(kitchen["prototype"], 0.25)
        self.assertEqual(2, kitchen["observation_count"])
        self.assertEqual(1, kitchen["guess_count"])
        self.assertEqual(1, kitchen["correct_count"])
        self.assertEqual(0, kitchen["incorrect_count"])

        self.assertIn("agent online", output.lines)
        self.assertIn("where am i", output.lines)
        self.assertIn("guess: kitchen (confidence=1.00)", output.lines)
        self.assertIn("goodbye", output.lines)

        events = self._parse_events()
        mutation_kinds = [
            event["mutation_kind"] for event in events if event["event_type"] == "memory_mutation"
        ]
        self.assertIn("model_created", mutation_kinds)
        self.assertIn("merge_observation", mutation_kinds)

    def test_invalid_inputs_and_wrong_guess_trigger_reprompt_and_alias_preserving_correction(
        self,
    ) -> None:
        _, output = self._run(
            [
                "oops",
                "-1",
                "0.75",
                "   ",
                "office",
                "0.75",
                "maybe",
                "0",
                "   ",
                "hallway",
                "quit",
            ]
        )

        reloaded = MemoryStore(self.memory_path)
        hallway = next(
            model for model in reloaded.inspect_models() if model["canonical_name"] == "hallway"
        )
        self.assertAlmostEqual(hallway["prototype"], 0.75)
        self.assertEqual(2, hallway["observation_count"])
        self.assertEqual(1, hallway["guess_count"])
        self.assertEqual(0, hallway["correct_count"])
        self.assertEqual(1, hallway["incorrect_count"])
        self.assertIn("office", hallway["aliases"])

        self.assertGreaterEqual(output.lines.count("where am i"), 2)
        self.assertIn("invalid observation: enter a number between 0.0 and 1.0", output.lines)
        self.assertIn("label cannot be empty", output.lines)
        self.assertIn("invalid feedback: enter 1 or 0", output.lines)
        self.assertIn("guess: office (confidence=1.00)", output.lines)

        events = self._parse_events()
        correction_event = next(
            event
            for event in events
            if event["event_type"] == "memory_mutation"
            and event["mutation_kind"] == "label_correction"
        )
        self.assertEqual("office", correction_event["old_record"]["canonical_name"])
        self.assertEqual("hallway", correction_event["new_record"]["canonical_name"])
        self.assertIn("office", correction_event["new_record"]["aliases"])

    def test_yes_no_feedback_accepted(self) -> None:
        self._run(["0.5", "lab", "0.5", "yes", "quit"])

        reloaded = MemoryStore(self.memory_path)
        lab = next(model for model in reloaded.inspect_models() if model["canonical_name"] == "lab")
        self.assertEqual(1, lab["correct_count"])

    def test_verbose_mode_shows_phase8_banner_and_summary(self) -> None:
        _, output = self._run(["0.25", "kitchen", "quit"], quiet=False)

        combined = "\n".join(output.lines)
        self.assertIn("Tree-of-Thought Location Agent", combined)
        self.assertIn("Phase 8", combined)
        self.assertIn("rename", combined)
        self.assertIn("alias", combined)
        self.assertIn("contain", combined)
        self.assertIn("overlap", combined)
        self.assertIn("concept", combined)
        self.assertIn("relate", combined)
        self.assertIn("adapter", combined.lower())
        self.assertIn("Session Summary", combined)
        self.assertIn("goodbye", output.lines)

    def test_noisy_match_guesses_with_reduced_confidence(self) -> None:
        _, output = self._run(["0.25", "kitchen", "0.253", "yes", "quit"])

        guess_lines = [line for line in output.lines if "kitchen" in line and "confidence" in line]
        self.assertTrue(len(guess_lines) >= 1)
        reloaded = MemoryStore(self.memory_path)
        kitchen = next(
            model for model in reloaded.inspect_models() if model["canonical_name"] == "kitchen"
        )
        self.assertEqual(1, kitchen["correct_count"])

    def test_far_observation_triggers_unknown(self) -> None:
        _, output = self._run(["0.25", "kitchen", "0.90", "lobby", "quit"])

        self.assertIn("where am i", output.lines)
        reloaded = MemoryStore(self.memory_path)
        lobby = next(
            model for model in reloaded.inspect_models() if model["canonical_name"] == "lobby"
        )
        self.assertIsNotNone(lobby)

    def test_uncertain_guess_rejected_then_new_label(self) -> None:
        _, output = self._run(["0.25", "kitchen", "0.296", "no", "bathroom", "yes", "quit"])

        combined = "\n".join(output.lines)
        self.assertIn("uncertain", combined)
        reloaded = MemoryStore(self.memory_path)
        names = {model["canonical_name"] for model in reloaded.inspect_models()}
        self.assertIn("bathroom", names)

    def test_near_collision_guard_warns_user(self) -> None:
        _, output = self._run(["0.25", "kitchen", "0.296", "no", "bathroom", "yes", "quit"])

        self.assertIn("near:", "\n".join(output.lines))

    def test_near_collision_guard_skip(self) -> None:
        _, output = self._run(["0.25", "kitchen", "0.296", "no", "bathroom", "no", "quit"])

        self.assertIn("skipped", "\n".join(output.lines))
        reloaded = MemoryStore(self.memory_path)
        names = {model["canonical_name"] for model in reloaded.inspect_models()}
        self.assertNotIn("bathroom", names)

    def test_noisy_confirmation_merges_observation_into_model(self) -> None:
        self._run(["0.25", "kitchen", "0.253", "yes", "quit"])

        reloaded = MemoryStore(self.memory_path)
        kitchen = next(
            model for model in reloaded.inspect_models() if model["canonical_name"] == "kitchen"
        )
        self.assertAlmostEqual(kitchen["prototype"], (0.25 + 0.253) / 2, places=5)
        self.assertEqual(2, kitchen["observation_count"])
        self.assertGreater(kitchen["spread"], 0.0)

    def test_repeated_confirmations_shift_prototype_progressively(self) -> None:
        self._run(["0.25", "kitchen", "0.253", "yes", "0.248", "yes", "quit"])

        reloaded = MemoryStore(self.memory_path)
        kitchen = next(
            model for model in reloaded.inspect_models() if model["canonical_name"] == "kitchen"
        )
        expected_proto = (0.25 + 0.253 + 0.248) / 3
        self.assertAlmostEqual(kitchen["prototype"], expected_proto, places=5)
        self.assertEqual(3, kitchen["observation_count"])

    def test_reusing_existing_label_merges_instead_of_conflicting(self) -> None:
        _, output = self._run(["0.1", "Point one", "0.15", "yes", "0.2", "Point one", "quit"])

        combined = "\n".join(output.lines)
        self.assertNotIn("label conflict", combined)
        reloaded = MemoryStore(self.memory_path)
        point_one = next(
            model for model in reloaded.inspect_models() if model["canonical_name"] == "Point one"
        )
        self.assertEqual(3, point_one["observation_count"])
        self.assertAlmostEqual((0.1 + 0.15 + 0.2) / 3, point_one["prototype"], places=5)

    def test_learned_span_is_inferred_by_default(self) -> None:
        _, output = self._run(
            ["0.1", "Point one", "0.3", "Point one", "yes", "0.28", "yes", "quit"]
        )

        combined = "\n".join(output.lines)
        self.assertIn("guess: Point one", combined)
        reloaded = MemoryStore(self.memory_path)
        point_one = next(
            model for model in reloaded.inspect_models() if model["canonical_name"] == "Point one"
        )
        self.assertEqual(3, point_one["observation_count"])

    def test_inspect_command_shows_labels_aliases_and_ids(self) -> None:
        _, output = self._run(
            [
                "0.25",
                "kitchen",
                "alias",
                "kitchen",
                "galley",
                "inspect",
                "quit",
            ]
        )

        combined = "\n".join(output.lines)
        self.assertIn("kitchen|galley|label-", combined)
        self.assertIn("0.250000", combined)

    def test_inspect_command_appends_relation_fields_in_quiet_mode(self) -> None:
        _, output = self._run(
            [
                "0.10",
                "house",
                "0.20",
                "bedroom",
                "contain",
                "house",
                "bedroom",
                "inspect",
                "quit",
            ]
        )

        combined = "\n".join(output.lines)
        self.assertIn("house||label-", combined)
        self.assertIn("|bedroom,house||house|", combined)
        self.assertIn("||house|", combined)

    def test_merge_event_logged(self) -> None:
        self._run(["0.25", "kitchen", "0.253", "yes", "quit"])

        events = self._parse_events()
        merge_event = next(
            event
            for event in events
            if event["event_type"] == "memory_mutation"
            and event["mutation_kind"] == "merge_observation"
        )
        self.assertEqual(1, merge_event["old_record"]["observation_count"])
        self.assertEqual(2, merge_event["new_record"]["observation_count"])
        self.assertEqual("kitchen", merge_event["new_record"]["canonical_name"])

    def test_rename_command_updates_canonical_name_and_logs(self) -> None:
        feeder, output = self._run(["0.25", "kitchen", "rename", "kitchen", "break room", "quit"])

        reloaded = MemoryStore(self.memory_path)
        renamed = next(
            model for model in reloaded.inspect_models() if model["canonical_name"] == "break room"
        )
        self.assertIn("kitchen", renamed["aliases"])
        self.assertIn("renamed: kitchen -> break room", output.lines)
        self.assertIn("rename from: ", feeder.prompts)
        self.assertIn("rename to: ", feeder.prompts)

        events = self._parse_events()
        rename_event = next(
            event
            for event in events
            if event["event_type"] == "memory_mutation"
            and event["mutation_kind"] == "label_renamed"
        )
        self.assertEqual("kitchen", rename_event["old_record"]["canonical_name"])
        self.assertEqual("break room", rename_event["new_record"]["canonical_name"])

    def test_alias_command_adds_alias_and_logs(self) -> None:
        feeder, output = self._run(["0.25", "kitchen", "alias", "kitchen", "galley", "quit"])

        reloaded = MemoryStore(self.memory_path)
        kitchen = next(
            model for model in reloaded.inspect_models() if model["canonical_name"] == "kitchen"
        )
        self.assertEqual(["galley"], kitchen["aliases"])
        self.assertIn("alias-added: galley -> kitchen", output.lines)
        self.assertIn("alias for: ", feeder.prompts)
        self.assertIn("alias name: ", feeder.prompts)

        events = self._parse_events()
        alias_event = next(
            event
            for event in events
            if event["event_type"] == "memory_mutation"
            and event["mutation_kind"] == "label_alias_added"
        )
        self.assertEqual([], alias_event["old_record"]["aliases"])
        self.assertEqual(["galley"], alias_event["new_record"]["aliases"])

    def test_alias_added_name_resolves_after_restart(self) -> None:
        self._run(["0.25", "kitchen", "alias", "kitchen", "galley", "quit"])

        reloaded = MemoryStore(self.memory_path)
        resolved = reloaded.lookup_by_label_name("galley")

        self.assertIsNotNone(resolved)
        model, label = resolved
        self.assertEqual(label.label_id, model.label_id)
        self.assertEqual("kitchen", label.canonical_name)

    def test_sensor_path_can_be_learned_then_recognized(self) -> None:
        _, output = self._run(
            [
                f"sense {self.sensor_path}",
                "bedroom",
                f"sense {self.sensor_path}",
                "yes",
                "quit",
            ]
        )

        combined = "\n".join(output.lines)
        self.assertIn("sensor: new image", combined)
        self.assertIn("sensor: recognized image", combined)
        self.assertIn("guess: bedroom (confidence=1.00)", combined)

        reloaded = MemoryStore(self.memory_path)
        recognized = reloaded.lookup_sensor_binding(
            SensorObservation.from_path(str(self.sensor_path)).fingerprint
        )
        self.assertIsNotNone(recognized)

        events = self._parse_events()
        sensor_events = [event for event in events if event.get("observation_kind") == "sensor"]
        self.assertGreaterEqual(len(sensor_events), 2)

    def test_sensor_learn_multiple_images_to_different_locations(self) -> None:
        img_b = Path(self.temporary_directory.name) / "lobby.png"
        img_b.write_bytes(b"lobby-image-data")

        _, output = self._run(
            [
                f"sense {self.sensor_path}",
                "bedroom",
                f"sense {img_b}",
                "lobby",
                f"sense {self.sensor_path}",
                "yes",
                f"sense {img_b}",
                "yes",
                "quit",
            ]
        )

        combined = "\n".join(output.lines)
        self.assertEqual(combined.count("sensor: new image"), 2)
        self.assertEqual(combined.count("sensor: recognized image"), 2)

        reloaded = MemoryStore(self.memory_path)
        for img, expected in [(self.sensor_path, "bedroom"), (img_b, "lobby")]:
            result = reloaded.lookup_sensor_binding(
                SensorObservation.from_path(str(img)).fingerprint
            )
            self.assertIsNotNone(result)
            _, _, label = result
            self.assertEqual(expected, label.canonical_name)

    def test_sensor_wrong_guess_correction(self) -> None:
        _, output = self._run(
            [
                f"sense {self.sensor_path}",
                "bedroom",
                f"sense {self.sensor_path}",
                "no",
                "office",
                "quit",
            ]
        )

        combined = "\n".join(output.lines)
        self.assertIn("sensor: new image", combined)
        self.assertIn("sensor: recognized image", combined)
        self.assertIn("guess: bedroom (confidence=1.00)", combined)

        reloaded = MemoryStore(self.memory_path)
        result = reloaded.lookup_sensor_binding(
            SensorObservation.from_path(str(self.sensor_path)).fingerprint
        )
        self.assertIsNotNone(result)
        _, _, label = result
        self.assertEqual("office", label.canonical_name)

        events = self._parse_events()
        correction_event = next(
            (e for e in events if e.get("mutation_kind") == "sensor_binding_updated"),
            None,
        )
        self.assertIsNotNone(correction_event)

    def test_sensor_unknown_image_prompts_label(self) -> None:
        feeder, output = self._run(
            [
                f"sense {self.sensor_path}",
                "bedroom",
                "quit",
            ]
        )

        combined = "\n".join(output.lines)
        self.assertIn("sensor: new image", combined)
        self.assertIn("label: ", feeder.prompts)

    def test_sensor_multiple_images_same_location(self) -> None:
        img_b = Path(self.temporary_directory.name) / "bedroom2.jpg"
        img_b.write_bytes(b"second-bedroom-image")

        _, output = self._run(
            [
                f"sense {self.sensor_path}",
                "bedroom",
                f"sense {img_b}",
                "bedroom",
                f"sense {self.sensor_path}",
                "yes",
                f"sense {img_b}",
                "yes",
                "quit",
            ]
        )

        combined = "\n".join(output.lines)
        self.assertIn("guess: bedroom (confidence=1.00)", combined)

        reloaded = MemoryStore(self.memory_path)
        for img in [self.sensor_path, img_b]:
            result = reloaded.lookup_sensor_binding(
                SensorObservation.from_path(str(img)).fingerprint
            )
            self.assertIsNotNone(result)
            _, _, label = result
            self.assertEqual("bedroom", label.canonical_name)

    def test_contain_command_adds_relation_and_logs(self) -> None:
        feeder, output = self._run(
            [
                "0.10",
                "house",
                "0.20",
                "bedroom",
                "contain",
                "house",
                "bedroom",
                "quit",
            ]
        )

        reloaded = MemoryStore(self.memory_path)
        bedroom = next(
            model for model in reloaded.inspect_models() if model["canonical_name"] == "bedroom"
        )
        self.assertEqual(["house"], bedroom["contained_by"])
        self.assertIn("contains: house -> bedroom", output.lines)
        self.assertIn("contain parent: ", feeder.prompts)
        self.assertIn("contain child: ", feeder.prompts)

        events = self._parse_events()
        relation_event = next(
            event
            for event in events
            if event["event_type"] == "memory_mutation"
            and event["mutation_kind"] == "location_containment_added"
        )
        self.assertEqual("contains", relation_event["new_record"]["relation_kind"])

    def test_overlap_command_deduplicates_reverse_pair(self) -> None:
        _, output = self._run(
            [
                "0.10",
                "hallway",
                "0.20",
                "doorway",
                "overlap",
                "hallway",
                "doorway",
                "overlap",
                "doorway",
                "hallway",
                "quit",
            ]
        )

        combined = "\n".join(output.lines)
        self.assertIn("overlaps: hallway <-> doorway", combined)
        self.assertIn("unchanged overlaps: doorway <-> hallway", combined)
        reloaded = MemoryStore(self.memory_path)
        hallway = next(
            model for model in reloaded.inspect_models() if model["canonical_name"] == "hallway"
        )
        self.assertEqual(["doorway"], hallway["overlaps"])

    def test_relation_commands_treat_self_links_as_noops(self) -> None:
        _, output = self._run(["0.10", "house", "contain", "house", "house", "quit"])

        self.assertIn("unchanged contains: house -> house", "\n".join(output.lines))
        reloaded = MemoryStore(self.memory_path)
        house = next(
            model for model in reloaded.inspect_models() if model["canonical_name"] == "house"
        )
        self.assertEqual([], house["contains"])

    def test_active_context_is_emitted_after_nested_recognition(self) -> None:
        _, output = self._run(
            [
                "0.10",
                "house",
                "0.20",
                "bedroom",
                "contain",
                "house",
                "bedroom",
                "0.20",
                "yes",
                "quit",
            ]
        )

        self.assertIn("active-context: bedroom, house", "\n".join(output.lines))

    def test_rename_and_alias_conflicts_reprompt(self) -> None:
        feeder, output = self._run(
            [
                "0.25",
                "kitchen",
                "0.90",
                "lobby",
                "rename",
                "kitchen",
                "lobby",
                "break room",
                "alias",
                "break room",
                "lobby",
                "galley",
                "quit",
            ]
        )

        combined = "\n".join(output.lines)
        self.assertIn('label conflict: label "lobby" is already in use', combined)
        self.assertGreaterEqual(feeder.prompts.count("rename to: "), 2)
        self.assertGreaterEqual(feeder.prompts.count("alias name: "), 2)

    def test_reset_command_confirmed_clears_memory(self) -> None:
        _, output = self._run(
            ["0.25", "kitchen", "0.90", "lobby", "reset", "yes", "inspect", "quit"]
        )

        combined = "\n".join(output.lines)
        self.assertIn("reset: 2 models cleared", combined)
        self.assertIn("empty", combined)

        reloaded = MemoryStore(self.memory_path)
        self.assertEqual([], reloaded.inspect_models())

    def test_reset_command_cancelled_preserves_memory(self) -> None:
        _, output = self._run(["0.25", "kitchen", "reset", "no", "inspect", "quit"])

        self.assertIn("reset cancelled", "\n".join(output.lines))
        reloaded = MemoryStore(self.memory_path)
        self.assertEqual(1, len(reloaded.inspect_models()))

    def test_reset_event_logged(self) -> None:
        self._run(["0.25", "kitchen", "reset", "yes", "quit"])

        events = self._parse_events()
        reset_events = [
            event
            for event in events
            if event["event_type"] == "memory_mutation" and event["mutation_kind"] == "memory_reset"
        ]
        self.assertEqual(1, len(reset_events))

    def test_context_command_shows_active_context(self) -> None:
        feeder, output = self._run(
            [
                "0.10",
                "house",
                "0.20",
                "bedroom",
                "contain",
                "house",
                "bedroom",
                "context",
                "bedroom",
                "quit",
            ]
        )

        combined = "\n".join(output.lines)
        self.assertIn("active-context: bedroom, house", combined)
        self.assertIn("context for: ", "\n".join(feeder.prompts))
        events = self._parse_events()
        context_events = [
            event
            for event in events
            if event["event_type"] == "query" and "context_command" in (event.get("notes") or "")
        ]
        self.assertEqual(1, len(context_events))
        self.assertIn("bedroom", context_events[0]["notes"])

    def test_context_command_no_relations(self) -> None:
        _, output = self._run(["0.10", "house", "context", "house", "quit"])

        self.assertIn("active-context: house", "\n".join(output.lines))

    def test_context_command_unknown_location(self) -> None:
        feeder, output = self._run(["0.10", "house", "context", "nowhere", "house", "quit"])

        combined = "\n".join(output.lines)
        self.assertIn("label not found: nowhere", combined)
        self.assertIn("active-context: house", combined)

    def test_contain_cycle_is_rejected_in_session(self) -> None:
        _, output = self._run(
            [
                "0.10",
                "house",
                "0.20",
                "bedroom",
                "contain",
                "house",
                "bedroom",
                "contain",
                "bedroom",
                "house",
                "quit",
            ]
        )

        combined = "\n".join(output.lines)
        self.assertIn("contains: house -> bedroom", combined)
        self.assertIn("cycle rejected:", combined)

    def test_concept_command_creates_concept(self) -> None:
        _, output = self._run(
            [
                "concept",
                "warmth",
                "primitive",
                "quit",
            ]
        )
        combined = "\n".join(output.lines)
        self.assertIn("concept: warmth (primitive)", combined)
        reloaded = MemoryStore(self.memory_path)
        node = reloaded.lookup_concept_by_name("warmth")
        self.assertIsNotNone(node)
        self.assertEqual("primitive", node.concept_kind)

    def test_concept_command_rejects_invalid_kind(self) -> None:
        _, output = self._run(
            [
                "concept",
                "warmth",
                "bogus",
                "primitive",
                "quit",
            ]
        )
        combined = "\n".join(output.lines)
        self.assertIn("invalid kind: bogus", combined)
        self.assertIn("concept: warmth (primitive)", combined)

    def test_concept_command_existing_concept(self) -> None:
        _, output = self._run(
            [
                "concept",
                "warmth",
                "primitive",
                "concept",
                "warmth",
                "composite",
                "quit",
            ]
        )
        combined = "\n".join(output.lines)
        self.assertIn("concept: warmth (primitive)", combined)
        self.assertIn("concept exists: warmth", combined)

    def test_relate_command_links_concepts(self) -> None:
        _, output = self._run(
            [
                "concept",
                "warmth",
                "primitive",
                "concept",
                "comfort",
                "composite",
                "relate",
                "warmth",
                "comfort",
                "supports",
                "quit",
            ]
        )
        combined = "\n".join(output.lines)
        self.assertIn("linked: warmth -supports-> comfort", combined)
        reloaded = MemoryStore(self.memory_path)
        rels = reloaded.concept_relations("warmth")
        self.assertIn("comfort", rels["supports"])

    def test_relate_command_rejects_invalid_kind(self) -> None:
        _, output = self._run(
            [
                "concept",
                "warmth",
                "primitive",
                "concept",
                "comfort",
                "composite",
                "relate",
                "warmth",
                "comfort",
                "contains",
                "supports",
                "quit",
            ]
        )
        combined = "\n".join(output.lines)
        self.assertIn("invalid relation: contains", combined)
        self.assertIn("linked: warmth -supports-> comfort", combined)

    def test_relate_command_unknown_concept_retries(self) -> None:
        _, output = self._run(
            [
                "concept",
                "warmth",
                "primitive",
                "concept",
                "comfort",
                "composite",
                "relate",
                "nonexistent",
                "warmth",
                "comfort",
                "supports",
                "quit",
            ]
        )
        combined = "\n".join(output.lines)
        self.assertIn("concept not found: nonexistent", combined)
        self.assertIn("linked: warmth -supports-> comfort", combined)

    def test_concepts_command_shows_all(self) -> None:
        _, output = self._run(
            [
                "concept",
                "warmth",
                "primitive",
                "concept",
                "comfort",
                "composite",
                "relate",
                "warmth",
                "comfort",
                "supports",
                "concepts",
                "quit",
            ]
        )
        combined = "\n".join(output.lines)
        self.assertIn("comfort(composite)", combined)
        self.assertIn("warmth(primitive)", combined)
        self.assertIn("-supports-> comfort", combined)

    def test_concepts_command_empty(self) -> None:
        _, output = self._run(
            [
                "concepts",
                "quit",
            ]
        )
        combined = "\n".join(output.lines)
        self.assertIn("concepts: (none)", combined)


if __name__ == "__main__":
    unittest.main()
