"""Tests for sensor-adapter plugin discovery via entry points."""

from __future__ import annotations

import unittest
from typing import Any
from unittest import mock

from location_agent import SensorAdapter, load_adapters
from location_agent.models import ObservationBundle


class _FakeBundle:
    """Stand-in object — `load_adapters` only invokes the constructor and
    `modality` accessor, so we never call observe() in these tests."""


class FakeAudioAdapter(SensorAdapter):
    @property
    def adapter_id(self) -> str:
        return "fake-audio-v0"

    @property
    def modality(self) -> str:
        return "audio"

    def observe(self, raw_input: str) -> ObservationBundle:  # pragma: no cover
        raise NotImplementedError


class NotAnAdapter:
    """Class that does NOT inherit from SensorAdapter."""

    @property
    def modality(self) -> str:
        return "rogue"


def _fake_entry_point(name: str, target: type) -> Any:
    ep = mock.Mock()
    ep.name = name
    ep.load = mock.Mock(return_value=target)
    return ep


class PluginDiscoveryTests(unittest.TestCase):
    def test_registered_adapter_is_discovered(self) -> None:
        ep = _fake_entry_point("audio", FakeAudioAdapter)
        with mock.patch("location_agent.plugins._select_entry_points", return_value=(ep,)):
            adapters = load_adapters()
        self.assertIn("audio", adapters)
        self.assertIsInstance(adapters["audio"], FakeAudioAdapter)

    def test_non_sensor_adapter_is_rejected(self) -> None:
        ep = _fake_entry_point("rogue", NotAnAdapter)
        with (
            mock.patch("location_agent.plugins._select_entry_points", return_value=(ep,)),
            self.assertLogs("location_agent.plugins", level="WARNING") as cm,
        ):
            adapters = load_adapters()
        self.assertNotIn("rogue", adapters)
        self.assertTrue(any("does not produce a SensorAdapter" in msg for msg in cm.output))

    def test_failed_load_is_skipped_with_warning(self) -> None:
        ep = mock.Mock()
        ep.name = "broken"
        ep.load = mock.Mock(side_effect=ImportError("boom"))
        with (
            mock.patch("location_agent.plugins._select_entry_points", return_value=(ep,)),
            self.assertLogs("location_agent.plugins", level="WARNING") as cm,
        ):
            adapters = load_adapters()
        self.assertNotIn("broken", adapters)
        self.assertTrue(any("failed to load" in msg for msg in cm.output))

    def test_empty_entry_point_group_returns_empty_dict(self) -> None:
        with mock.patch("location_agent.plugins._select_entry_points", return_value=()):
            self.assertEqual(load_adapters(), {})


if __name__ == "__main__":
    unittest.main()
