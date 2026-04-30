"""Storage protocol for the public SDK.

`MemoryStorage` is the abstract surface used in type hints. The default
concrete implementation is `LocalJSONStore` (alias of the legacy
``MemoryStore`` class), which persists state to a single JSON file under
``runtime/``.

Future implementations (e.g. ``FirestoreStore`` for the hosted web app in
Release Phase R3) only need to satisfy this protocol — no public consumer
should depend on the concrete class type.

This protocol is a *structural* contract checked at runtime via
``typing.runtime_checkable``. It enumerates the subset of methods that the
``Agent`` facade and the interactive ``SessionController`` actually call.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from location_agent.models import (
    LabelNode,
    LocationModel,
    NormalizedObservation,
    ObservationBundle,
    SensorBinding,
    SensorObservation,
)


@runtime_checkable
class MemoryStorage(Protocol):
    """Structural contract for memory backends.

    The current local-JSON implementation (``MemoryStore`` aka
    ``LocalJSONStore``) satisfies this protocol. New backends only need to
    implement the listed methods to be usable by ``Agent`` or any other
    SDK consumer.
    """

    @property
    def guess_threshold(self) -> float: ...

    @property
    def tolerance(self) -> float: ...

    def find_nearest(
        self, observation: NormalizedObservation
    ) -> tuple[LocationModel | None, float]: ...

    def lookup_by_id(self, location_id: str) -> LocationModel | None: ...

    def lookup_by_label_name(self, name: str) -> tuple[LocationModel, LabelNode] | None: ...

    def lookup_sensor_binding(
        self, fingerprint: str
    ) -> tuple[SensorBinding, LocationModel, LabelNode] | None: ...

    def learn_location(
        self, observation: NormalizedObservation, label: str
    ) -> tuple[None, LocationModel]: ...

    def record_correct_guess(
        self,
        observation: NormalizedObservation,
        matched_model: LocationModel | None = ...,
    ) -> tuple[LocationModel, LocationModel]: ...

    def correct_location(
        self,
        observation: NormalizedObservation,
        new_label: str,
        matched_model: LocationModel | None = ...,
    ) -> tuple[dict[str, Any], dict[str, Any]]: ...

    def store_bundle(self, bundle: ObservationBundle) -> None: ...

    def get_bundle(self, bundle_id: str) -> ObservationBundle | None: ...

    def bind_sensor_bundle(
        self,
        bundle: ObservationBundle,
        sensor_observation: SensorObservation,
        label: str,
    ) -> tuple[dict[str, Any] | None, dict[str, Any], bool]: ...

    def snapshot_location(self, model: LocationModel | str) -> dict[str, Any]: ...

    def inspect_models(self) -> list[dict[str, Any]]: ...

    def reset_memory(self) -> int: ...
