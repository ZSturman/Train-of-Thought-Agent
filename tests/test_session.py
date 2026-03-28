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
        record = reloaded.lookup(NormalizedObservation.parse("0.25"))
        self.assertIsNotNone(record)
        self.assertEqual("kitchen", record.label)
        self.assertEqual(2, record.observation_count)
        self.assertEqual(1, record.guess_count)
        self.assertEqual(1, record.correct_count)
        self.assertEqual(0, record.incorrect_count)

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
        self.assertIn("create_location", mutation_kinds)
        self.assertIn("feedback_counters", mutation_kinds)

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
        record = reloaded.lookup(NormalizedObservation.parse("0.750000"))
        self.assertIsNotNone(record)
        self.assertEqual("hallway", record.label)
        self.assertEqual(2, record.observation_count)
        self.assertEqual(1, record.guess_count)
        self.assertEqual(0, record.correct_count)
        self.assertEqual(1, record.incorrect_count)

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
        """Verify that yes/no/y/n strings are accepted as feedback."""
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
        record = reloaded.lookup(NormalizedObservation.parse("0.5"))
        self.assertIsNotNone(record)
        self.assertEqual(1, record.correct_count)

    def test_verbose_mode_shows_banner_and_summary(self) -> None:
        """Verbose mode (quiet=False) emits a welcome banner and session summary."""
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
        self.assertIn("Phase 1", combined)
        self.assertIn("Session Summary", combined)
        self.assertIn("Observations entered", combined)
        self.assertIn("goodbye", output.lines)


if __name__ == "__main__":
    unittest.main()
