"""Tests for the public SDK surface (`from location_agent import ...`)."""

from __future__ import annotations

import unittest

import location_agent

EXPECTED_PUBLIC_NAMES = {
    "Agent",
    "AsyncAgent",
    "EventLogger",
    "ImageAdapter",
    "LabelConflictError",
    "LabelLookupError",
    "LabelNameError",
    "LearnResult",
    "LocalJSONStore",
    "MemoryStorage",
    "MemoryStore",
    "ObservationBundle",
    "ObservationError",
    "RecognitionResult",
    "RegionDescriptor",
    "SensorAdapter",
    "SensorObservationError",
    "SessionController",
    "__version__",
    "load_adapters",
}


class PublicAPITests(unittest.TestCase):
    def test_all_matches_expected(self) -> None:
        self.assertEqual(set(location_agent.__all__), EXPECTED_PUBLIC_NAMES)

    def test_all_names_importable(self) -> None:
        for name in location_agent.__all__:
            self.assertTrue(
                hasattr(location_agent, name),
                f"location_agent missing exported name {name!r}",
            )

    def test_public_callables_have_docstrings(self) -> None:
        # Skip plain string/version constants and test only types/functions.
        skip = {"__version__"}
        for name in location_agent.__all__:
            if name in skip:
                continue
            obj = getattr(location_agent, name)
            self.assertTrue(
                getattr(obj, "__doc__", None),
                f"public name {name!r} is missing a docstring",
            )

    def test_version_is_string(self) -> None:
        self.assertIsInstance(location_agent.__version__, str)
        self.assertTrue(location_agent.__version__)

    def test_memory_storage_is_runtime_checkable(self) -> None:
        from location_agent import LocalJSONStore, MemoryStorage

        # The Protocol must be runtime-checkable so SDK users can
        # validate alternate backends with isinstance().
        self.assertTrue(hasattr(MemoryStorage, "__instancecheck__"))
        # The shipped local-JSON implementation must satisfy it.
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            store = LocalJSONStore(Path(tmp) / "mem.json")
            self.assertIsInstance(store, MemoryStorage)

    def test_local_json_store_is_alias_of_memory_store(self) -> None:
        self.assertIs(location_agent.LocalJSONStore, location_agent.MemoryStore)


if __name__ == "__main__":
    unittest.main()
