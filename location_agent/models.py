from __future__ import annotations

import hashlib
import math
from pathlib import Path
from dataclasses import dataclass, replace
from datetime import datetime, timezone

SCHEMA_VERSION = 5
NORMALIZATION_DECIMALS = 6
DEFAULT_TOLERANCE = 0.05
DEFAULT_GUESS_THRESHOLD = 0.6
REINFORCEMENT_BOOST_PER_CONFIRM = 0.05
REINFORCEMENT_BOOST_CAP = 0.4
DEFAULT_OUTLIER_FACTOR = 3.0
ALLOWED_PROVENANCE_SOURCES = frozenset({"user", "sensor"})


class ObservationError(ValueError):
    """Raised when an observation cannot be parsed into the scalar range."""


class LabelNameError(ValueError):
    """Raised when a label name is empty after normalization."""


class SensorObservationError(ValueError):
    """Raised when a simulated sensor input path cannot be used."""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def validate_provenance_source(source: str) -> str:
    normalized = source.strip().casefold()
    if normalized not in ALLOWED_PROVENANCE_SOURCES:
        raise ValueError(f"unsupported provenance source: {source}")
    return normalized


def scalar_distance(a: float, b: float) -> float:
    """Absolute distance between two scalar observations."""
    return abs(a - b)


def distance_to_interval(value: float, lower: float, upper: float) -> float:
    """Distance from *value* to the closed interval [lower, upper]."""
    if lower > upper:
        lower, upper = upper, lower
    if lower <= value <= upper:
        return 0.0
    return min(abs(value - lower), abs(value - upper))


def distance_to_confidence(distance: float, tolerance: float) -> float:
    """Map distance to confidence using linear decay."""
    if distance < 0.0 or tolerance <= 0.0:
        return 0.0
    if distance > tolerance:
        return 0.0
    return 1.0 - 0.5 * (distance / tolerance)


def reinforced_confidence(
    base_confidence: float,
    correct_count: int,
) -> float:
    """Boost base confidence using accumulated correct confirmations."""
    if base_confidence <= 0.0 or correct_count <= 0:
        return base_confidence
    boost = min(correct_count * REINFORCEMENT_BOOST_PER_CONFIRM, REINFORCEMENT_BOOST_CAP)
    return min(base_confidence + boost, 1.0)


def compute_spread(values: list[float]) -> float:
    """Population standard deviation of *values*."""
    n = len(values)
    if n <= 1:
        return 0.0
    mean = sum(values) / n
    return math.sqrt(sum((v - mean) ** 2 for v in values) / n)


def normalize_label_name(raw_name: str) -> str:
    """Normalize a human-supplied label while preserving meaningful casing."""
    normalized = raw_name.strip()
    if not normalized:
        raise LabelNameError("label cannot be empty")
    return normalized


def label_lookup_key(raw_name: str) -> str:
    """Case-insensitive lookup key for canonical labels and aliases."""
    return normalize_label_name(raw_name).casefold()


def infer_media_kind(path: Path) -> str:
    suffix = path.suffix.casefold()
    if suffix in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}:
        return "image"
    if suffix in {".mp4", ".mov", ".avi", ".mkv", ".webm"}:
        return "video"
    if suffix in {".wav", ".mp3", ".ogg", ".m4a"}:
        return "audio"
    if suffix in {".txt", ".md", ".json", ".csv"}:
        return "text"
    return "binary"


@dataclass(frozen=True)
class NormalizedObservation:
    raw_input: str
    value: float
    key: str

    @classmethod
    def parse(cls, raw_input: str) -> "NormalizedObservation":
        stripped = raw_input.strip()
        if not stripped:
            raise ObservationError("invalid observation: enter a number between 0.0 and 1.0")
        try:
            value = float(stripped)
        except ValueError as exc:
            raise ObservationError("invalid observation: enter a number between 0.0 and 1.0") from exc
        if not 0.0 <= value <= 1.0:
            raise ObservationError("invalid observation: enter a number between 0.0 and 1.0")
        return cls(raw_input=raw_input, value=value, key=f"{value:.{NORMALIZATION_DECIMALS}f}")


@dataclass(frozen=True)
class SensorObservation:
    raw_path: str
    resolved_path: str
    fingerprint: str
    media_kind: str
    file_size: int

    @classmethod
    def from_path(cls, raw_path: str) -> "SensorObservation":
        normalized = raw_path.strip()
        if not normalized:
            raise SensorObservationError("sensor path cannot be empty")

        path = Path(normalized).expanduser().resolve()
        if not path.exists():
            raise SensorObservationError(f"sensor path not found: {path}")
        if not path.is_file():
            raise SensorObservationError(f"sensor path is not a file: {path}")

        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)

        stat = path.stat()
        return cls(
            raw_path=raw_path,
            resolved_path=str(path),
            fingerprint=digest.hexdigest(),
            media_kind=infer_media_kind(path),
            file_size=stat.st_size,
        )


# -- Phase 2 legacy (used only for migration) ---------------------------


@dataclass(frozen=True)
class LocationRecord:
    location_id: str
    observation_key: str
    observation_value: float
    label: str
    observation_count: int
    guess_count: int
    correct_count: int
    incorrect_count: int
    first_seen_at: str
    last_seen_at: str

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "LocationRecord":
        return cls(
            location_id=str(payload["location_id"]),
            observation_key=str(payload["observation_key"]),
            observation_value=float(payload["observation_value"]),
            label=str(payload["label"]),
            observation_count=int(payload["observation_count"]),
            guess_count=int(payload["guess_count"]),
            correct_count=int(payload["correct_count"]),
            incorrect_count=int(payload["incorrect_count"]),
            first_seen_at=str(payload["first_seen_at"]),
            last_seen_at=str(payload["last_seen_at"]),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "location_id": self.location_id,
            "observation_key": self.observation_key,
            "observation_value": self.observation_value,
            "label": self.label,
            "observation_count": self.observation_count,
            "guess_count": self.guess_count,
            "correct_count": self.correct_count,
            "incorrect_count": self.incorrect_count,
            "first_seen_at": self.first_seen_at,
            "last_seen_at": self.last_seen_at,
        }


# -- Phase 4 label graph -----------------------------------------------


@dataclass(frozen=True)
class RenameRecord:
    old_name: str
    new_name: str
    renamed_at: str

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "RenameRecord":
        return cls(
            old_name=str(payload["old_name"]),
            new_name=str(payload["new_name"]),
            renamed_at=str(payload["renamed_at"]),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "old_name": self.old_name,
            "new_name": self.new_name,
            "renamed_at": self.renamed_at,
        }


@dataclass(frozen=True)
class LabelNode:
    label_id: str
    canonical_name: str
    aliases: tuple[str, ...]
    rename_history: tuple[RenameRecord, ...]
    created_at: str
    updated_at: str
    provenance_source: str = "user"
    provenance_detail: str = "manual_label"

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "LabelNode":
        raw_history = payload.get("rename_history", [])
        return cls(
            label_id=str(payload["label_id"]),
            canonical_name=str(payload["canonical_name"]),
            aliases=tuple(str(alias) for alias in payload.get("aliases", [])),
            rename_history=tuple(RenameRecord.from_dict(entry) for entry in raw_history),
            created_at=str(payload["created_at"]),
            updated_at=str(payload["updated_at"]),
            provenance_source=validate_provenance_source(
                str(payload.get("provenance_source", "user"))
            ),
            provenance_detail=str(payload.get("provenance_detail", "manual_label")),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "label_id": self.label_id,
            "canonical_name": self.canonical_name,
            "aliases": list(self.aliases),
            "rename_history": [entry.to_dict() for entry in self.rename_history],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "provenance_source": self.provenance_source,
            "provenance_detail": self.provenance_detail,
        }

    def with_alias(self, alias: str) -> "LabelNode":
        alias_name = normalize_label_name(alias)
        alias_key = alias_name.casefold()
        if alias_key == self.canonical_name.casefold():
            return self
        for existing in self.aliases:
            if existing.casefold() == alias_key:
                return self
        return replace(
            self,
            aliases=self.aliases + (alias_name,),
            updated_at=utc_now_iso(),
        )

    def with_renamed_canonical(self, new_name: str) -> "LabelNode":
        normalized = normalize_label_name(new_name)
        if normalized.casefold() == self.canonical_name.casefold():
            return self

        timestamp = utc_now_iso()
        remaining_aliases = tuple(
            alias for alias in self.aliases if alias.casefold() != normalized.casefold()
        )
        if all(alias.casefold() != self.canonical_name.casefold() for alias in remaining_aliases):
            remaining_aliases = remaining_aliases + (self.canonical_name,)

        return replace(
            self,
            canonical_name=normalized,
            aliases=remaining_aliases,
            rename_history=self.rename_history + (
                RenameRecord(
                    old_name=self.canonical_name,
                    new_name=normalized,
                    renamed_at=timestamp,
                ),
            ),
            updated_at=timestamp,
        )

    def all_names(self) -> tuple[str, ...]:
        return (self.canonical_name,) + self.aliases


# -- Phase 4 location model --------------------------------------------


@dataclass(frozen=True)
class LocationModel:
    location_id: str
    label_id: str
    prototype: float | None
    observation_values: tuple[float, ...]
    observation_count: int
    spread: float
    guess_count: int
    correct_count: int
    incorrect_count: int
    first_seen_at: str
    last_seen_at: str
    provenance_source: str = "user"
    provenance_detail: str = "scalar_observation"

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "LocationModel":
        raw_values = payload.get("observation_values", [])
        values = tuple(float(v) for v in raw_values)  # type: ignore[union-attr]
        raw_prototype = payload.get("prototype")
        return cls(
            location_id=str(payload["location_id"]),
            label_id=str(payload["label_id"]),
            prototype=None if raw_prototype is None else float(raw_prototype),
            observation_values=values,
            observation_count=int(payload["observation_count"]),
            spread=float(payload["spread"]),
            guess_count=int(payload["guess_count"]),
            correct_count=int(payload["correct_count"]),
            incorrect_count=int(payload["incorrect_count"]),
            first_seen_at=str(payload["first_seen_at"]),
            last_seen_at=str(payload["last_seen_at"]),
            provenance_source=validate_provenance_source(
                str(payload.get("provenance_source", "user"))
            ),
            provenance_detail=str(payload.get("provenance_detail", "scalar_observation")),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "location_id": self.location_id,
            "label_id": self.label_id,
            "prototype": self.prototype,
            "observation_values": list(self.observation_values),
            "observation_count": self.observation_count,
            "spread": self.spread,
            "guess_count": self.guess_count,
            "correct_count": self.correct_count,
            "incorrect_count": self.incorrect_count,
            "first_seen_at": self.first_seen_at,
            "last_seen_at": self.last_seen_at,
            "provenance_source": self.provenance_source,
            "provenance_detail": self.provenance_detail,
        }

    def with_merged_observation(self, value: float) -> "LocationModel":
        new_values = self.observation_values + (value,)
        new_count = len(new_values)
        new_prototype = sum(new_values) / len(new_values)
        new_spread = compute_spread(list(new_values))
        return replace(
            self,
            prototype=new_prototype,
            observation_values=new_values,
            observation_count=new_count,
            spread=new_spread,
            last_seen_at=utc_now_iso(),
        )

    def with_last_seen(self) -> "LocationModel":
        return replace(self, last_seen_at=utc_now_iso())

    def observation_bounds(self) -> tuple[float | None, float | None]:
        if self.observation_values:
            return min(self.observation_values), max(self.observation_values)
        if self.prototype is not None:
            return self.prototype, self.prototype
        return None, None

    def distance_to_value(self, value: float) -> float:
        lower, upper = self.observation_bounds()
        if lower is None or upper is None:
            return math.inf
        return distance_to_interval(value, lower, upper)

    @classmethod
    def from_record(cls, record: LocationRecord, *, label_id: str = "") -> "LocationModel":
        return cls(
            location_id=record.location_id,
            label_id=label_id,
            prototype=record.observation_value,
            observation_values=(record.observation_value,),
            observation_count=record.observation_count,
            spread=0.0,
            guess_count=record.guess_count,
            correct_count=record.correct_count,
            incorrect_count=record.incorrect_count,
            first_seen_at=record.first_seen_at,
            last_seen_at=record.last_seen_at,
            provenance_source="user",
            provenance_detail="migrated_scalar_observation",
        )

    @classmethod
    def empty(
        cls,
        *,
        location_id: str,
        label_id: str,
        provenance_source: str,
        provenance_detail: str,
    ) -> "LocationModel":
        timestamp = utc_now_iso()
        return cls(
            location_id=location_id,
            label_id=label_id,
            prototype=None,
            observation_values=(),
            observation_count=0,
            spread=0.0,
            guess_count=0,
            correct_count=0,
            incorrect_count=0,
            first_seen_at=timestamp,
            last_seen_at=timestamp,
            provenance_source=validate_provenance_source(provenance_source),
            provenance_detail=provenance_detail,
        )


@dataclass(frozen=True)
class ConceptNode:
    concept_id: str
    concept_name: str
    aliases: tuple[str, ...]
    created_at: str
    updated_at: str
    provenance_source: str
    provenance_detail: str

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "ConceptNode":
        return cls(
            concept_id=str(payload["concept_id"]),
            concept_name=str(payload["concept_name"]),
            aliases=tuple(str(alias) for alias in payload.get("aliases", [])),
            created_at=str(payload["created_at"]),
            updated_at=str(payload["updated_at"]),
            provenance_source=validate_provenance_source(
                str(payload.get("provenance_source", "user"))
            ),
            provenance_detail=str(payload.get("provenance_detail", "manual_concept")),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "concept_id": self.concept_id,
            "concept_name": self.concept_name,
            "aliases": list(self.aliases),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "provenance_source": self.provenance_source,
            "provenance_detail": self.provenance_detail,
        }

    def all_names(self) -> tuple[str, ...]:
        return (self.concept_name,) + self.aliases


@dataclass(frozen=True)
class GraphEdge:
    edge_id: str
    source_node_id: str
    source_node_type: str
    target_node_id: str
    target_node_type: str
    relation_kind: str
    created_at: str
    updated_at: str
    provenance_source: str
    provenance_detail: str

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "GraphEdge":
        return cls(
            edge_id=str(payload["edge_id"]),
            source_node_id=str(payload["source_node_id"]),
            source_node_type=str(payload["source_node_type"]),
            target_node_id=str(payload["target_node_id"]),
            target_node_type=str(payload["target_node_type"]),
            relation_kind=str(payload["relation_kind"]),
            created_at=str(payload["created_at"]),
            updated_at=str(payload["updated_at"]),
            provenance_source=validate_provenance_source(
                str(payload.get("provenance_source", "user"))
            ),
            provenance_detail=str(payload.get("provenance_detail", "graph_edge")),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "edge_id": self.edge_id,
            "source_node_id": self.source_node_id,
            "source_node_type": self.source_node_type,
            "target_node_id": self.target_node_id,
            "target_node_type": self.target_node_type,
            "relation_kind": self.relation_kind,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "provenance_source": self.provenance_source,
            "provenance_detail": self.provenance_detail,
        }


@dataclass(frozen=True)
class SensorBinding:
    sensor_id: str
    fingerprint: str
    media_kind: str
    media_path: str
    location_id: str
    created_at: str
    updated_at: str
    provenance_source: str
    provenance_detail: str

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "SensorBinding":
        return cls(
            sensor_id=str(payload["sensor_id"]),
            fingerprint=str(payload["fingerprint"]),
            media_kind=str(payload["media_kind"]),
            media_path=str(payload["media_path"]),
            location_id=str(payload["location_id"]),
            created_at=str(payload["created_at"]),
            updated_at=str(payload["updated_at"]),
            provenance_source=validate_provenance_source(
                str(payload.get("provenance_source", "sensor"))
            ),
            provenance_detail=str(payload.get("provenance_detail", "sensor_path")),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "sensor_id": self.sensor_id,
            "fingerprint": self.fingerprint,
            "media_kind": self.media_kind,
            "media_path": self.media_path,
            "location_id": self.location_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "provenance_source": self.provenance_source,
            "provenance_detail": self.provenance_detail,
        }

    def with_location(self, location_id: str, media_path: str) -> "SensorBinding":
        return replace(
            self,
            location_id=location_id,
            media_path=media_path,
            updated_at=utc_now_iso(),
        )


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    owner_node_id: str
    owner_node_type: str
    source_kind: str
    channel: str
    value_text: str | None
    observation_value: float | None
    sensor_fingerprint: str | None
    media_kind: str | None
    media_path: str | None
    created_at: str

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "EvidenceRecord":
        raw_observation_value = payload.get("observation_value")
        return cls(
            evidence_id=str(payload["evidence_id"]),
            owner_node_id=str(payload["owner_node_id"]),
            owner_node_type=str(payload["owner_node_type"]),
            source_kind=validate_provenance_source(str(payload.get("source_kind", "user"))),
            channel=str(payload["channel"]),
            value_text=None if payload.get("value_text") is None else str(payload["value_text"]),
            observation_value=None
            if raw_observation_value is None
            else float(raw_observation_value),
            sensor_fingerprint=None
            if payload.get("sensor_fingerprint") is None
            else str(payload["sensor_fingerprint"]),
            media_kind=None if payload.get("media_kind") is None else str(payload["media_kind"]),
            media_path=None if payload.get("media_path") is None else str(payload["media_path"]),
            created_at=str(payload["created_at"]),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "evidence_id": self.evidence_id,
            "owner_node_id": self.owner_node_id,
            "owner_node_type": self.owner_node_type,
            "source_kind": self.source_kind,
            "channel": self.channel,
            "value_text": self.value_text,
            "observation_value": self.observation_value,
            "sensor_fingerprint": self.sensor_fingerprint,
            "media_kind": self.media_kind,
            "media_path": self.media_path,
            "created_at": self.created_at,
        }
