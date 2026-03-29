from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from location_agent.models import LocationModel, LocationRecord, NormalizedObservation, SCHEMA_VERSION, utc_now_iso


class EventLogger:
    """Append-only JSONL logger for runtime events."""

    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(
        self,
        event_type: str,
        *,
        session_id: str,
        observation: NormalizedObservation | None = None,
        guessed_label: str | None = None,
        confidence: float | None = None,
        feedback: int | None = None,
        mutation_kind: str | None = None,
        old_record: LocationRecord | LocationModel | None = None,
        new_record: LocationRecord | LocationModel | None = None,
        notes: str | None = None,
    ) -> None:
        def _serialize(rec: LocationRecord | LocationModel | None) -> dict[str, Any] | None:
            if rec is None:
                return None
            return rec.to_dict()

        payload: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "timestamp": utc_now_iso(),
            "event_type": event_type,
            "session_id": session_id,
            "observation_key": observation.key if observation else None,
            "observation_value": observation.value if observation else None,
            "guessed_label": guessed_label,
            "confidence": confidence,
            "feedback": feedback,
            "mutation_kind": mutation_kind,
            "old_record": _serialize(old_record),
            "new_record": _serialize(new_record),
            "notes": notes,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, sort_keys=True))
            handle.write("\n")
