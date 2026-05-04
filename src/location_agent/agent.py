"""High-level programmatic facade over `MemoryStore` + `EventLogger` + adapters.

`Agent` is the single entry point recommended for SDK consumers (the
HTTP API in R3 and web app in R4 both build on it). It wraps storage,
logging, and sensor-adapter discovery so callers do not need to wire
three objects together.

`AsyncAgent` is a thin async wrapper over `Agent` for use in FastAPI
workers and other async callers. All blocking operations are offloaded
to the default thread executor via :func:`asyncio.to_thread`.

The interactive CLI loop (`SessionController`) is deliberately *not*
re-implemented here — it remains the CLI's I/O-coupled driver. For
programmatic use, prefer `Agent` or `AsyncAgent`.

Example
-------
>>> from location_agent import Agent
>>> agent = Agent()
>>> agent.learn_scalar(0.25, "kitchen")
>>> result = agent.recognize_scalar(0.253)
>>> print(result.label, result.confidence)
kitchen 0.97
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from location_agent.logging import EventLogger
from location_agent.memory import MemoryStore
from location_agent.models import (
    ImageAdapter,
    NormalizedObservation,
    ObservationBundle,
    SensorAdapter,
    SensorObservation,
    SensorObservationError,
)
from location_agent.plugins import load_adapters
from location_agent.storage import MemoryStorage


@dataclass(frozen=True)
class RecognitionResult:
    """Outcome of a recognition call.

    ``is_known`` is ``True`` when the agent matched an existing learned
    location with confidence ≥ ``store.guess_threshold``; for sensor
    inputs, ``True`` indicates an exact-fingerprint binding match.
    """

    is_known: bool
    label: str | None
    confidence: float
    location_id: str | None
    bundle: ObservationBundle | None = None


@dataclass(frozen=True)
class LearnResult:
    """Outcome of a learn call."""

    location_id: str
    label: str
    snapshot: dict[str, Any]


class Agent:
    """Programmatic facade for the location-agent SDK.

    Parameters
    ----------
    runtime_dir:
        Directory used for the default `LocalJSONStore` and event log.
        Defaults to ``./runtime``.
    store:
        Optional pre-constructed storage backend. Must satisfy
        `MemoryStorage`. Defaults to a `LocalJSONStore` rooted at
        ``runtime_dir/location_memory.json``.
    logger:
        Optional pre-constructed `EventLogger`. Defaults to one writing
        to ``runtime_dir/agent_events.jsonl``.
    adapters:
        Optional mapping of modality -> `SensorAdapter`. Defaults to the
        built-in `ImageAdapter` plus any registered via the
        ``tot.adapters`` entry-point group.
    session_id:
        Optional session identifier used in event logs.
    """

    def __init__(
        self,
        runtime_dir: Path | str | None = None,
        *,
        store: MemoryStorage | None = None,
        logger: EventLogger | None = None,
        adapters: dict[str, SensorAdapter] | None = None,
        session_id: str | None = None,
    ) -> None:
        runtime_path = Path(runtime_dir) if runtime_dir is not None else Path.cwd() / "runtime"
        runtime_path.mkdir(parents=True, exist_ok=True)
        self._store: MemoryStorage = store or MemoryStore(runtime_path / "location_memory.json")
        self._logger = logger or EventLogger(runtime_path / "agent_events.jsonl")
        if adapters is None:
            adapters = load_adapters()
            adapters.setdefault("image", ImageAdapter())
        self._adapters: dict[str, SensorAdapter] = adapters
        self.session_id = session_id or uuid.uuid4().hex

    # -- accessors -------------------------------------------------------

    @property
    def store(self) -> MemoryStorage:
        return self._store

    @property
    def logger(self) -> EventLogger:
        return self._logger

    @property
    def adapters(self) -> dict[str, SensorAdapter]:
        return dict(self._adapters)

    # -- scalar API ------------------------------------------------------

    def learn_scalar(self, value: float, label: str) -> LearnResult:
        """Learn a new location associating *value* with *label*."""
        observation = NormalizedObservation.parse(str(value))
        _, model = self._store.learn_location(observation, label)
        snapshot = self._store.snapshot_location(model)
        self._logger.log(
            "memory_mutation",
            session_id=self.session_id,
            observation=observation,
            mutation_kind="model_created",
            new_record=snapshot,
            notes="agent.learn_scalar",
        )
        return LearnResult(
            location_id=model.location_id,
            label=str(snapshot["canonical_name"]),
            snapshot=snapshot,
        )

    def recognize_scalar(self, value: float) -> RecognitionResult:
        """Recognize a scalar observation against learned locations."""
        observation = NormalizedObservation.parse(str(value))
        model, confidence = self._store.find_nearest(observation)
        self._logger.log(
            "observation",
            session_id=self.session_id,
            observation=observation,
            confidence=confidence,
            notes="agent.recognize_scalar",
        )
        if model is None or confidence < self._store.guess_threshold:
            return RecognitionResult(
                is_known=False,
                label=None,
                confidence=confidence,
                location_id=model.location_id if model is not None else None,
            )
        snapshot = self._store.snapshot_location(model)
        return RecognitionResult(
            is_known=True,
            label=str(snapshot["canonical_name"]),
            confidence=confidence,
            location_id=model.location_id,
        )

    def confirm_scalar(self, value: float, location_id: str) -> dict[str, Any]:
        """Confirm a recognition was correct; reinforces the matched model."""
        observation = NormalizedObservation.parse(str(value))
        model = self._store.lookup_by_id(location_id)
        if model is None:
            raise KeyError(f"unknown location_id: {location_id}")
        _, updated = self._store.record_correct_guess(observation, matched_model=model)
        return self._store.snapshot_location(updated)

    def correct_scalar(self, value: float, location_id: str, new_label: str) -> dict[str, Any]:
        """Correct a wrong recognition by relabeling the matched model."""
        observation = NormalizedObservation.parse(str(value))
        model = self._store.lookup_by_id(location_id)
        if model is None:
            raise KeyError(f"unknown location_id: {location_id}")
        _, new_snapshot = self._store.correct_location(observation, new_label, matched_model=model)
        return new_snapshot

    # -- sensor API ------------------------------------------------------

    def sense(self, raw_input: str | Path, modality: str = "image") -> RecognitionResult:
        """Route raw sensor input through the adapter and look up bindings.

        Returns a `RecognitionResult` with ``is_known=False`` if the
        sensor input has not been seen before. The bundle is always
        attached to the result for downstream `learn_sensor` /
        `confirm_sensor` calls.
        """
        adapter = self._adapters.get(modality)
        if adapter is None:
            raise KeyError(f"no adapter registered for modality {modality!r}")
        bundle = adapter.observe(str(raw_input))
        sensor_obs = self._sensor_observation_from_bundle(adapter, bundle)
        if sensor_obs is None:
            return RecognitionResult(
                is_known=False, label=None, confidence=0.0, location_id=None, bundle=bundle
            )
        recognized = self._store.lookup_sensor_binding(sensor_obs.fingerprint)
        self._logger.log(
            "observation",
            session_id=self.session_id,
            sensor_observation=sensor_obs,
            bundle_id=bundle.bundle_id,
            adapter_id=bundle.adapter_id,
            notes="agent.sense",
        )
        if recognized is None:
            return RecognitionResult(
                is_known=False, label=None, confidence=0.0, location_id=None, bundle=bundle
            )
        _, model, label_node = recognized
        return RecognitionResult(
            is_known=True,
            label=label_node.canonical_name,
            confidence=1.0,
            location_id=model.location_id,
            bundle=bundle,
        )

    def learn_sensor(
        self, bundle: ObservationBundle, label: str, modality: str = "image"
    ) -> dict[str, Any]:
        """Bind *bundle* to *label*, creating a sensor binding entry."""
        adapter = self._adapters.get(modality)
        if adapter is None:
            raise KeyError(f"no adapter registered for modality {modality!r}")
        sensor_obs = self._sensor_observation_from_bundle(adapter, bundle)
        if sensor_obs is None:
            raise SensorObservationError("could not derive sensor observation from bundle")
        _, snapshot, _ = self._store.bind_sensor_bundle(bundle, sensor_obs, label)
        return snapshot

    # -- inspection / lifecycle -----------------------------------------

    def inspect(self) -> dict[str, Any]:
        """Return a JSON-serializable snapshot of learned state."""
        return {
            "session_id": self.session_id,
            "guess_threshold": self._store.guess_threshold,
            "tolerance": self._store.tolerance,
            "locations": self._store.inspect_models(),
            "adapters": sorted(self._adapters.keys()),
        }

    def reset(self) -> int:
        """Clear all learned location memory. Returns count of cleared models."""
        return self._store.reset_memory()

    # -- helpers ---------------------------------------------------------

    @staticmethod
    def _sensor_observation_from_bundle(
        adapter: SensorAdapter, bundle: ObservationBundle
    ) -> SensorObservation | None:
        helper = getattr(adapter, "sensor_observation_from_bundle", None)
        if helper is None:
            return None
        result = helper(bundle)
        return result if isinstance(result, SensorObservation) else None


class AsyncAgent:
    """Thin async wrapper over :class:`Agent` for FastAPI workers and async callers.

    All blocking :class:`Agent` methods are offloaded to the default thread
    executor via :func:`asyncio.to_thread`, keeping the synchronous ``Agent``
    intact for CLI and notebook use.

    Parameters
    ----------
    runtime_dir, store, logger, adapters, session_id:
        Forwarded to :class:`Agent` when *agent* is not supplied.
    agent:
        Optional pre-constructed :class:`Agent`. When supplied, the other
        constructor parameters are ignored.
    """

    def __init__(
        self,
        runtime_dir: Path | str | None = None,
        *,
        store: MemoryStorage | None = None,
        logger: EventLogger | None = None,
        adapters: dict[str, SensorAdapter] | None = None,
        session_id: str | None = None,
        agent: Agent | None = None,
    ) -> None:
        if agent is not None:
            self._agent = agent
        else:
            self._agent = Agent(
                runtime_dir,
                store=store,
                logger=logger,
                adapters=adapters,
                session_id=session_id,
            )

    @property
    def agent(self) -> Agent:
        return self._agent

    async def learn_scalar(self, value: float, label: str) -> LearnResult:
        return await asyncio.to_thread(self._agent.learn_scalar, value, label)

    async def recognize_scalar(self, value: float) -> RecognitionResult:
        return await asyncio.to_thread(self._agent.recognize_scalar, value)

    async def confirm_scalar(self, value: float, location_id: str) -> dict[str, Any]:
        return await asyncio.to_thread(self._agent.confirm_scalar, value, location_id)

    async def correct_scalar(
        self, value: float, location_id: str, new_label: str
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            self._agent.correct_scalar, value, location_id, new_label
        )

    async def sense(self, raw_input: str | Path, modality: str = "image") -> RecognitionResult:
        return await asyncio.to_thread(self._agent.sense, raw_input, modality)

    async def learn_sensor(
        self, bundle: ObservationBundle, label: str, modality: str = "image"
    ) -> dict[str, Any]:
        return await asyncio.to_thread(self._agent.learn_sensor, bundle, label, modality)

    async def inspect(self) -> dict[str, Any]:
        return await asyncio.to_thread(self._agent.inspect)

    async def reset(self) -> int:
        return await asyncio.to_thread(self._agent.reset)
