from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from location_agent.logging import EventLogger
from location_agent.memory import MemoryStore
from location_agent.models import NormalizedObservation
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

    def _parse_events(self) -> list[dict[str, object]]:
        with self.event_log_path.open("r", encoding="utf-8") as handle:
            return [json.loads(line) for line in handle if line.strip()]

    def test_unknown_then_known_correct_guess_persists_and_logs(self) -> None:
        feeder = InputFeeder(["0.25", "kitchen", "0.250000", "1", "quit"])
        output = OutputCollector()
        controller = SessionController(
            store=MemoryStore(self.memory_path),
            event_logger=EventLogger(self.event_log_path),
            input_func=feeder,
            output_func=output,
            session_id="test-session",
            quiet=True,
        )

        controller.run()

        reloaded = MemoryStore(self.memory_path)
        # Find the kitchen model.
        models = reloaded.inspect_models()
        kitchen = next(m for m in models if m["label"] == "kitchen")
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
        event_types = [event["event_type"] for event in events]
        self.assertIn("observation", event_types)
        self.assertIn("decision", event_types)
        self.assertIn("feedback", event_types)
        mutation_events = [event for event in events if event["event_type"] == "memory_mutation"]
        mutation_kinds = [event["mutation_kind"] for event in mutation_events]
        self.assertIn("model_created", mutation_kinds)
        self.assertIn("merge_observation", mutation_kinds)

    def test_invalid_inputs_and_wrong_guess_trigger_reprompt_and_correction(self) -> None:
        feeder = InputFeeder(
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
        output = OutputCollector()
        controller = SessionController(
            store=MemoryStore(self.memory_path),
            event_logger=EventLogger(self.event_log_path),
            input_func=feeder,
            output_func=output,
            session_id="test-session",
            quiet=True,
        )

        controller.run()

        reloaded = MemoryStore(self.memory_path)
        models = reloaded.inspect_models()
        hallway = next(m for m in models if m["label"] == "hallway")
        self.assertAlmostEqual(hallway["prototype"], 0.75)
        self.assertEqual(2, hallway["observation_count"])
        self.assertEqual(1, hallway["guess_count"])
        self.assertEqual(0, hallway["correct_count"])
        self.assertEqual(1, hallway["incorrect_count"])

        self.assertGreaterEqual(output.lines.count("where am i"), 2)
        self.assertIn("invalid observation: enter a number between 0.0 and 1.0", output.lines)
        self.assertIn("label cannot be empty", output.lines)
        self.assertIn("invalid feedback: enter 1 or 0", output.lines)
        self.assertIn("guess: office (confidence=1.00)", output.lines)

        events = self._parse_events()
        mutation_events = [event for event in events if event["event_type"] == "memory_mutation"]
        correction_event = next(
            event for event in mutation_events if event["mutation_kind"] == "label_correction"
        )
        self.assertEqual("office", correction_event["old_record"]["label"])
        self.assertEqual("hallway", correction_event["new_record"]["label"])

    def test_yes_no_feedback_accepted(self) -> None:
        feeder = InputFeeder(["0.5", "lab", "0.5", "yes", "quit"])
        output = OutputCollector()
        controller = SessionController(
            store=MemoryStore(self.memory_path),
            event_logger=EventLogger(self.event_log_path),
            input_func=feeder,
            output_func=output,
            session_id="test-session",
            quiet=True,
        )

        controller.run()

        reloaded = MemoryStore(self.memory_path)
        models = reloaded.inspect_models()
        lab = next(m for m in models if m["label"] == "lab")
        self.assertEqual(1, lab["correct_count"])

    def test_verbose_mode_shows_banner_and_summary(self) -> None:
        feeder = InputFeeder(["0.25", "kitchen", "quit"])
        output = OutputCollector()
        controller = SessionController(
            store=MemoryStore(self.memory_path),
            event_logger=EventLogger(self.event_log_path),
            input_func=feeder,
            output_func=output,
            session_id="test-session",
            quiet=False,
        )

        controller.run()

        combined = "\n".join(output.lines)
        self.assertIn("Tree-of-Thought Location Agent", combined)
        self.assertIn("Phase 3", combined)
        self.assertIn("Session Summary", combined)
        self.assertIn("Observations entered", combined)
        self.assertIn("Observations merged", combined)
        self.assertIn("goodbye", output.lines)

    # -- Phase 2 regressions adapted for Phase 3 -------------------------

    def test_noisy_match_guesses_with_reduced_confidence(self) -> None:
        feeder = InputFeeder(["0.25", "kitchen", "0.253", "yes", "quit"])
        output = OutputCollector()
        controller = SessionController(
            store=MemoryStore(self.memory_path),
            event_logger=EventLogger(self.event_log_path),
            input_func=feeder,
            output_func=output,
            session_id="test-session",
            quiet=True,
        )

        controller.run()

        guess_lines = [l for l in output.lines if "kitchen" in l and "confidence" in l]
        self.assertTrue(len(guess_lines) >= 1)
        reloaded = MemoryStore(self.memory_path)
        models = reloaded.inspect_models()
        kitchen = next(m for m in models if m["label"] == "kitchen")
        self.assertEqual(1, kitchen["correct_count"])

    def test_far_observation_triggers_unknown(self) -> None:
        feeder = InputFeeder(["0.25", "kitchen", "0.90", "lobby", "yes", "quit"])
        output = OutputCollector()
        controller = SessionController(
            store=MemoryStore(self.memory_path),
            event_logger=EventLogger(self.event_log_path),
            input_func=feeder,
            output_func=output,
            session_id="test-session",
            quiet=True,
        )

        controller.run()

        self.assertIn("where am i", output.lines)
        reloaded = MemoryStore(self.memory_path)
        models = reloaded.inspect_models()
        lobby = next(m for m in models if m["label"] == "lobby")
        self.assertIsNotNone(lobby)

    def test_uncertain_guess_rejected_then_new_label(self) -> None:
        feeder = InputFeeder([
            "0.25", "kitchen",
            "0.296",
            "no",
            "bathroom",
            "yes",
            "quit",
        ])
        output = OutputCollector()
        controller = SessionController(
            store=MemoryStore(self.memory_path),
            event_logger=EventLogger(self.event_log_path),
            input_func=feeder,
            output_func=output,
            session_id="test-session",
            quiet=True,
        )

        controller.run()

        combined = "\n".join(output.lines)
        self.assertIn("uncertain", combined)

    def test_near_collision_guard_warns_user(self) -> None:
        feeder = InputFeeder([
            "0.25", "kitchen",
            "0.296",
            "no",
            "bathroom",
            "yes",
            "quit",
        ])
        output = OutputCollector()
        controller = SessionController(
            store=MemoryStore(self.memory_path),
            event_logger=EventLogger(self.event_log_path),
            input_func=feeder,
            output_func=output,
            session_id="test-session",
            quiet=True,
        )

        controller.run()

        combined = "\n".join(output.lines)
        self.assertIn("near:", combined)

    def test_near_collision_guard_skip(self) -> None:
        feeder = InputFeeder([
            "0.25", "kitchen",
            "0.296",
            "no",
            "bathroom",
            "no",
            "quit",
        ])
        output = OutputCollector()
        controller = SessionController(
            store=MemoryStore(self.memory_path),
            event_logger=EventLogger(self.event_log_path),
            input_func=feeder,
            output_func=output,
            session_id="test-session",
            quiet=True,
        )

        controller.run()

        combined = "\n".join(output.lines)
        self.assertIn("skipped", combined)
        # 0.296 should not have been learned.
        reloaded = MemoryStore(self.memory_path)
        models = reloaded.inspect_models()
        labels = {m["label"] for m in models}
        self.assertNotIn("bathroom", labels)

    # -- Phase 3: Merge and inspect tests ---------------------------------

    def test_noisy_confirmation_merges_observation_into_model(self) -> None:
        """Confirm a noisy match → observation value is merged into the model."""
        feeder = InputFeeder([
            "0.25", "kitchen",     # learn kitchen
            "0.253", "yes",        # noisy match, confirm → merge
            "quit",
        ])
        output = OutputCollector()
        controller = SessionController(
            store=MemoryStore(self.memory_path),
            event_logger=EventLogger(self.event_log_path),
            input_func=feeder,
            output_func=output,
            session_id="test-session",
            quiet=True,
        )

        controller.run()

        reloaded = MemoryStore(self.memory_path)
        models = reloaded.inspect_models()
        kitchen = next(m for m in models if m["label"] == "kitchen")
        # Prototype should have shifted from 0.25 toward 0.253.
        self.assertAlmostEqual(kitchen["prototype"], (0.25 + 0.253) / 2, places=5)
        self.assertEqual(2, kitchen["observation_count"])
        self.assertGreater(kitchen["spread"], 0.0)

    def test_repeated_confirmations_shift_prototype_progressively(self) -> None:
        """Multiple noisy confirmations progressively shift the prototype."""
        feeder = InputFeeder([
            "0.25", "kitchen",     # learn
            "0.253", "yes",        # merge 1
            "0.248", "yes",        # merge 2
            "quit",
        ])
        output = OutputCollector()
        controller = SessionController(
            store=MemoryStore(self.memory_path),
            event_logger=EventLogger(self.event_log_path),
            input_func=feeder,
            output_func=output,
            session_id="test-session",
            quiet=True,
        )

        controller.run()

        reloaded = MemoryStore(self.memory_path)
        models = reloaded.inspect_models()
        kitchen = next(m for m in models if m["label"] == "kitchen")
        expected_proto = (0.25 + 0.253 + 0.248) / 3
        self.assertAlmostEqual(kitchen["prototype"], expected_proto, places=5)
        self.assertEqual(3, kitchen["observation_count"])

    def test_inspect_command_shows_models(self) -> None:
        """Typing 'inspect' shows model stats."""
        feeder = InputFeeder([
            "0.25", "kitchen",
            "0.90", "lobby",
            "inspect",
            "quit",
        ])
        output = OutputCollector()
        controller = SessionController(
            store=MemoryStore(self.memory_path),
            event_logger=EventLogger(self.event_log_path),
            input_func=feeder,
            output_func=output,
            session_id="test-session",
            quiet=True,
        )

        controller.run()

        combined = "\n".join(output.lines)
        self.assertIn("kitchen", combined)
        self.assertIn("lobby", combined)
        self.assertIn("0.250000", combined)
        self.assertIn("0.900000", combined)

    def test_merge_event_logged(self) -> None:
        """Merge operations log mutation events with 'merge_observation' kind."""
        feeder = InputFeeder(["0.25", "kitchen", "0.253", "yes", "quit"])
        output = OutputCollector()
        controller = SessionController(
            store=MemoryStore(self.memory_path),
            event_logger=EventLogger(self.event_log_path),
            input_func=feeder,
            output_func=output,
            session_id="test-session",
            quiet=True,
        )

        controller.run()

        events = self._parse_events()
        mutation_events = [e for e in events if e["event_type"] == "memory_mutation"]
        merge_events = [e for e in mutation_events if e["mutation_kind"] == "merge_observation"]
        self.assertGreaterEqual(len(merge_events), 1)
        # The new record should have observation_values with 2 entries.
        new_rec = merge_events[0]["new_record"]
        self.assertEqual(2, len(new_rec["observation_values"]))


if __name__ == "__main__":
    unittest.main()
