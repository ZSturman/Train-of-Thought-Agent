"""Stub Firestore-backed memory storage.

The concrete implementation lands in Release Phase R3 alongside the hosted
HTTP API. This stub exists so that the public SDK can import a
``FirestoreStore`` symbol and so that the protocol contract can be
validated at type-check time.
"""

from __future__ import annotations

from typing import Any

from location_agent.models import (
    LabelNode,
    LocationModel,
    NormalizedObservation,
    ObservationBundle,
    SensorBinding,
    SensorObservation,
)


class FirestoreStore:
    """Placeholder for the Firestore-backed `MemoryStorage` implementation.

    All methods raise ``NotImplementedError``. R3 will provide a working
    implementation that satisfies the ``MemoryStorage`` protocol.
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        raise NotImplementedError(
            "FirestoreStore is not yet implemented. It lands in Release Phase R3. "
            "Use LocalJSONStore for local-first storage in R2."
        )

    @property
    def guess_threshold(self) -> float:  # pragma: no cover - stub
        raise NotImplementedError

    @property
    def tolerance(self) -> float:  # pragma: no cover - stub
        raise NotImplementedError

    def find_nearest(
        self, observation: NormalizedObservation
    ) -> tuple[LocationModel | None, float]:  # pragma: no cover - stub
        raise NotImplementedError

    def lookup_by_id(self, location_id: str) -> LocationModel | None:  # pragma: no cover - stub
        raise NotImplementedError

    def lookup_by_label_name(
        self, name: str
    ) -> tuple[LocationModel, LabelNode] | None:  # pragma: no cover - stub
        raise NotImplementedError

    def lookup_sensor_binding(
        self, fingerprint: str
    ) -> tuple[SensorBinding, LocationModel, LabelNode] | None:  # pragma: no cover - stub
        raise NotImplementedError

    def learn_location(
        self, observation: NormalizedObservation, label: str
    ) -> tuple[None, LocationModel]:  # pragma: no cover - stub
        raise NotImplementedError

    def record_correct_guess(
        self,
        observation: NormalizedObservation,
        matched_model: LocationModel | None = None,
    ) -> tuple[LocationModel, LocationModel]:  # pragma: no cover - stub
        raise NotImplementedError

    def correct_location(
        self,
        observation: NormalizedObservation,
        new_label: str,
        matched_model: LocationModel | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:  # pragma: no cover - stub
        raise NotImplementedError

    def store_bundle(self, bundle: ObservationBundle) -> None:  # pragma: no cover - stub
        raise NotImplementedError

    def get_bundle(self, bundle_id: str) -> ObservationBundle | None:  # pragma: no cover - stub
        raise NotImplementedError

    def bind_sensor_bundle(
        self,
        bundle: ObservationBundle,
        sensor_observation: SensorObservation,
        label: str,
    ) -> tuple[dict[str, Any] | None, dict[str, Any], bool]:  # pragma: no cover - stub
        raise NotImplementedError

    def snapshot_location(
        self, model: LocationModel | str
    ) -> dict[str, Any]:  # pragma: no cover - stub
        raise NotImplementedError

    def inspect_models(self) -> list[dict[str, Any]]:  # pragma: no cover - stub
        raise NotImplementedError

    def reset_memory(self) -> int:  # pragma: no cover - stub
        raise NotImplementedError
