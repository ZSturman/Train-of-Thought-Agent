"""End-to-end tests for the `Agent` facade using only public imports."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from location_agent import Agent, LearnResult, RecognitionResult


class AgentFacadeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.runtime = Path(self.tmp.name)

    def _agent(self) -> Agent:
        return Agent(runtime_dir=self.runtime)

    def test_learn_then_recognize_matches_label(self) -> None:
        agent = self._agent()
        learned = agent.learn_scalar(0.25, "kitchen")
        self.assertIsInstance(learned, LearnResult)
        self.assertEqual(learned.label, "kitchen")

        result = agent.recognize_scalar(0.253)
        self.assertIsInstance(result, RecognitionResult)
        self.assertTrue(result.is_known)
        self.assertEqual(result.label, "kitchen")
        self.assertEqual(result.location_id, learned.location_id)

    def test_recognize_unknown_returns_not_known(self) -> None:
        agent = self._agent()
        agent.learn_scalar(0.1, "alpha")
        result = agent.recognize_scalar(0.9)
        self.assertFalse(result.is_known)
        self.assertIsNone(result.label)

    def test_inspect_returns_serializable_snapshot(self) -> None:
        agent = self._agent()
        agent.learn_scalar(0.5, "beta")
        snapshot = agent.inspect()
        self.assertIn("locations", snapshot)
        self.assertIn("adapters", snapshot)
        self.assertIn("image", snapshot["adapters"])
        self.assertEqual(len(snapshot["locations"]), 1)

    def test_reset_clears_state(self) -> None:
        agent = self._agent()
        agent.learn_scalar(0.7, "gamma")
        cleared = agent.reset()
        self.assertGreaterEqual(cleared, 1)
        self.assertEqual(agent.inspect()["locations"], [])

    def test_default_adapters_include_image(self) -> None:
        agent = self._agent()
        self.assertIn("image", agent.adapters)


if __name__ == "__main__":
    unittest.main()
