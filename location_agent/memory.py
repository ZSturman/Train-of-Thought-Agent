from __future__ import annotations

import json
import uuid
from dataclasses import replace
from pathlib import Path
from typing import Any

from location_agent.models import (
    DEFAULT_GUESS_THRESHOLD,
    DEFAULT_OUTLIER_FACTOR,
    DEFAULT_TOLERANCE,
    LocationModel,
    LocationRecord,
    NormalizedObservation,
    SCHEMA_VERSION,
    distance_to_confidence,
    reinforced_confidence,
    scalar_distance,
    utc_now_iso,
)


class MemoryStore:
    """Persistent memory store backed by a single JSON file.

    Phase 3 stores *location models* keyed by ``location_id``.  Each model
    holds a running-mean prototype, the list of all merged observation values,
    population standard deviation (spread), and interaction counters.
    """

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load_or_initialize()

    # -- public properties -----------------------------------------------

    @property
    def confidence_policy(self) -> dict[str, Any]:
        return dict(self._data["confidence_policy"])

    @property
    def guess_threshold(self) -> float:
        return float(self._data["confidence_policy"]["guess_threshold"])

    @property
    def tolerance(self) -> float:
        return float(self._data["confidence_policy"]["tolerance"])

    @property
    def outlier_factor(self) -> float:
        return float(self._data["confidence_policy"].get("outlier_factor", DEFAULT_OUTLIER_FACTOR))

    @property
    def data(self) -> dict[str, Any]:
        return self._data

    # -- query -----------------------------------------------------------

    def find_nearest(
        self,
        observation: NormalizedObservation,
    ) -> tuple[LocationModel | None, float]:
        """Find the nearest location model by distance to its prototype.

        Returns the best matching LocationModel and its confidence score.
        """
        models = self._data["location_models"]

        best_model: LocationModel | None = None
        best_confidence: float = 0.0

        tol = self.tolerance
        for raw_model in models.values():
            proto = float(raw_model["prototype"])
            dist = scalar_distance(observation.value, proto)
            base_conf = distance_to_confidence(dist, tol)
            conf = reinforced_confidence(base_conf, int(raw_model.get("correct_count", 0)))
            if conf > best_confidence:
                best_confidence = conf
                best_model = LocationModel.from_dict(raw_model)

        return best_model, best_confidence

    def find_near_collision(
        self,
        observation: NormalizedObservation,
    ) -> LocationModel | None:
        """Return an existing model whose prototype is within tolerance, or None."""
        tol = self.tolerance
        for raw_model in self._data["location_models"].values():
            proto = float(raw_model["prototype"])
            if scalar_distance(observation.value, proto) <= tol:
                return LocationModel.from_dict(raw_model)
        return None

    def lookup_by_id(self, location_id: str) -> LocationModel | None:
        raw = self._data["location_models"].get(location_id)
        if raw is None:
            return None
        return LocationModel.from_dict(raw)

    def inspect_models(self) -> list[dict[str, Any]]:
        results = []
        for raw in self._data["location_models"].values():
            results.append({
                "location_id": raw["location_id"],
                "label": raw["label"],
                "prototype": raw["prototype"],
                "spread": raw["spread"],
                "observation_count": raw["observation_count"],
                "guess_count": raw["guess_count"],
                "correct_count": raw["correct_count"],
                "incorrect_count": raw["incorrect_count"],
            })
        return results

    def is_outlier(self, model: LocationModel, value: float) -> bool:
        threshold = self.outlier_factor * max(model.spread, self.tolerance)
        return scalar_distance(value, model.prototype) > threshold

    # -- mutations -------------------------------------------------------

    def learn_location(
        self,
        observation: NormalizedObservation,
        label: str,
    ) -> tuple[None, LocationModel]:
        timestamp = utc_now_iso()
        model = LocationModel(
            location_id=f"loc-{uuid.uuid4().hex[:12]}",
            label=label.strip(),
            prototype=observation.value,
            observation_values=(observation.value,),
            observation_count=1,
            spread=0.0,
            guess_count=0,
            correct_count=0,
            incorrect_count=0,
            first_seen_at=timestamp,
            last_seen_at=timestamp,
        )
        self._data["location_models"][model.location_id] = model.to_dict()
        self._save()
        return None, model

    def record_correct_guess(
        self,
        observation: NormalizedObservation,
        matched_model: LocationModel | None = None,
    ) -> tuple[LocationModel, LocationModel]:
        if matched_model is None:
            raise KeyError("matched_model is required in Phase 3")
        current = matched_model
        merged = current.with_merged_observation(observation.value)
        updated = replace(
            merged,
            guess_count=current.guess_count + 1,
            correct_count=current.correct_count + 1,
        )
        self._data["location_models"][current.location_id] = updated.to_dict()
        self._save()
        return current, updated

    def merge_observation(
        self,
        model: LocationModel,
        value: float,
    ) -> tuple[LocationModel, LocationModel]:
        updated = model.with_merged_observation(value)
        self._data["location_models"][model.location_id] = updated.to_dict()
        self._save()
        return model, updated

    def correct_location(
        self,
        observation: NormalizedObservation,
        new_label: str,
        matched_model: LocationModel | None = None,
    ) -> tuple[LocationModel, LocationModel]:
        if matched_model is None:
            raise KeyError("matched_model is required in Phase 3")
        current = matched_model
        updated = replace(
            current,
            label=new_label.strip(),
            observation_count=current.observation_count + 1,
            guess_count=current.guess_count + 1,
            incorrect_count=current.incorrect_count + 1,
            last_seen_at=utc_now_iso(),
        )
        self._data["location_models"][current.location_id] = updated.to_dict()
        self._save()
        return current, updated

    # -- persistence internals -------------------------------------------

    def _load_or_initialize(self) -> dict[str, Any]:
        if not self.path.exists():
            payload = self._empty_payload()
            self._write_payload(payload)
            return payload
        raw = self.path.read_text(encoding="utf-8")
        if not raw.strip():
            payload = self._empty_payload()
            self._write_payload(payload)
            return payload
        payload = json.loads(raw)
        payload.setdefault("schema_version", 1)
        payload.setdefault("confidence_policy", self._default_confidence_policy())
        payload.setdefault("created_at", utc_now_iso())
        payload.setdefault("updated_at", payload["created_at"])

        version = payload.get("schema_version", 1)

        # Migrate v1 → v2 (policy-only).
        if version < 2:
            policy = payload["confidence_policy"]
            policy["kind"] = "distance"
            policy["tolerance"] = DEFAULT_TOLERANCE
            policy["guess_threshold"] = DEFAULT_GUESS_THRESHOLD
            payload["schema_version"] = 2
            version = 2

        # Migrate v2 → v3 (structural: observation records → location models).
        if version < 3:
            old_locations = payload.get("locations_by_observation", {})
            models: dict[str, Any] = {}
            for _key, raw_record in old_locations.items():
                record = LocationRecord.from_dict(raw_record)
                model = LocationModel.from_record(record)
                models[model.location_id] = model.to_dict()
            payload["location_models"] = models
            payload.pop("locations_by_observation", None)
            policy = payload["confidence_policy"]
            policy.setdefault("outlier_factor", DEFAULT_OUTLIER_FACTOR)
            payload["schema_version"] = SCHEMA_VERSION
            version = SCHEMA_VERSION

        payload.setdefault("location_models", {})
        self._write_payload(payload)
        return payload

    def _empty_payload(self) -> dict[str, Any]:
        timestamp = utc_now_iso()
        return {
            "schema_version": SCHEMA_VERSION,
            "created_at": timestamp,
            "updated_at": timestamp,
            "confidence_policy": self._default_confidence_policy(),
            "location_models": {},
        }

    def _default_confidence_policy(self) -> dict[str, Any]:
        return {
            "kind": "distance",
            "tolerance": DEFAULT_TOLERANCE,
            "guess_threshold": DEFAULT_GUESS_THRESHOLD,
            "normalization_decimals": 6,
            "outlier_factor": DEFAULT_OUTLIER_FACTOR,
        }

    def _save(self) -> None:
        self._data["updated_at"] = utc_now_iso()
        self._write_payload(self._data)

    def _write_payload(self, payload: dict[str, Any]) -> None:
        temporary_path = self.path.with_suffix(self.path.suffix + ".tmp")
        serialized = json.dumps(payload, indent=2, sort_keys=True)
        temporary_path.write_text(f"{serialized}\n", encoding="utf-8")
        temporary_path.replace(self.path)
