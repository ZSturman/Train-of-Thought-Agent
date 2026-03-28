from __future__ import annotations

import json
import uuid
from dataclasses import replace
from pathlib import Path
from typing import Any

from location_agent.models import LocationRecord, NormalizedObservation, SCHEMA_VERSION, utc_now_iso


class MemoryStore:
    """Persistent Phase 1 memory store backed by a single JSON file."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._data = self._load_or_initialize()

    @property
    def confidence_policy(self) -> dict[str, Any]:
        return dict(self._data["confidence_policy"])

    @property
    def guess_threshold(self) -> float:
        return float(self._data["confidence_policy"]["guess_threshold"])

    @property
    def data(self) -> dict[str, Any]:
        return self._data

    def lookup(self, observation: NormalizedObservation) -> LocationRecord | None:
        record = self._data["locations_by_observation"].get(observation.key)
        if record is None:
            return None
        return LocationRecord.from_dict(record)

    def get_confidence(self, observation: NormalizedObservation) -> float:
        return 1.0 if observation.key in self._data["locations_by_observation"] else 0.0

    def learn_location(
        self,
        observation: NormalizedObservation,
        label: str,
    ) -> tuple[None, LocationRecord]:
        if observation.key in self._data["locations_by_observation"]:
            raise KeyError(f"observation key already exists: {observation.key}")
        timestamp = utc_now_iso()
        record = LocationRecord(
            location_id=f"loc-{uuid.uuid4().hex[:12]}",
            observation_key=observation.key,
            observation_value=observation.value,
            label=label.strip(),
            observation_count=1,
            guess_count=0,
            correct_count=0,
            incorrect_count=0,
            first_seen_at=timestamp,
            last_seen_at=timestamp,
        )
        self._data["locations_by_observation"][observation.key] = record.to_dict()
        self._save()
        return None, record

    def record_correct_guess(
        self,
        observation: NormalizedObservation,
    ) -> tuple[LocationRecord, LocationRecord]:
        current = self.lookup_or_raise(observation)
        updated = replace(
            current,
            observation_count=current.observation_count + 1,
            guess_count=current.guess_count + 1,
            correct_count=current.correct_count + 1,
            last_seen_at=utc_now_iso(),
        )
        self._data["locations_by_observation"][observation.key] = updated.to_dict()
        self._save()
        return current, updated

    def correct_location(
        self,
        observation: NormalizedObservation,
        new_label: str,
    ) -> tuple[LocationRecord, LocationRecord]:
        current = self.lookup_or_raise(observation)
        updated = replace(
            current,
            label=new_label.strip(),
            observation_count=current.observation_count + 1,
            guess_count=current.guess_count + 1,
            incorrect_count=current.incorrect_count + 1,
            last_seen_at=utc_now_iso(),
        )
        self._data["locations_by_observation"][observation.key] = updated.to_dict()
        self._save()
        return current, updated

    def lookup_or_raise(self, observation: NormalizedObservation) -> LocationRecord:
        record = self.lookup(observation)
        if record is None:
            raise KeyError(f"observation key not found: {observation.key}")
        return record

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
        payload.setdefault("schema_version", SCHEMA_VERSION)
        payload.setdefault("confidence_policy", self._default_confidence_policy())
        payload.setdefault("locations_by_observation", {})
        payload.setdefault("created_at", utc_now_iso())
        payload.setdefault("updated_at", payload["created_at"])
        return payload

    def _empty_payload(self) -> dict[str, Any]:
        timestamp = utc_now_iso()
        return {
            "schema_version": SCHEMA_VERSION,
            "created_at": timestamp,
            "updated_at": timestamp,
            "confidence_policy": self._default_confidence_policy(),
            "locations_by_observation": {},
        }

    def _default_confidence_policy(self) -> dict[str, Any]:
        return {
            "kind": "exact_match",
            "guess_threshold": 1.0,
            "normalization_decimals": 6,
        }

    def _save(self) -> None:
        self._data["updated_at"] = utc_now_iso()
        self._write_payload(self._data)

    def _write_payload(self, payload: dict[str, Any]) -> None:
        temporary_path = self.path.with_suffix(self.path.suffix + ".tmp")
        serialized = json.dumps(payload, indent=2, sort_keys=True)
        temporary_path.write_text(f"{serialized}\n", encoding="utf-8")
        temporary_path.replace(self.path)
