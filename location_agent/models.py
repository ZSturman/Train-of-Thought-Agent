from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from typing import List

SCHEMA_VERSION = 3
NORMALIZATION_DECIMALS = 6
DEFAULT_TOLERANCE = 0.05
DEFAULT_GUESS_THRESHOLD = 0.6
REINFORCEMENT_BOOST_PER_CONFIRM = 0.05
REINFORCEMENT_BOOST_CAP = 0.4
DEFAULT_OUTLIER_FACTOR = 3.0


class ObservationError(ValueError):
    """Raised when an observation cannot be parsed into the Phase 1 scalar range."""


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def scalar_distance(a: float, b: float) -> float:
    """Absolute distance between two scalar observations."""
    return abs(a - b)


def distance_to_confidence(distance: float, tolerance: float) -> float:
    """Map distance to confidence using linear decay.

    Returns 1.0 at distance=0, decays linearly to 0.5 at distance=tolerance,
    and returns 0.0 beyond tolerance.
    """
    if distance < 0.0 or tolerance <= 0.0:
        return 0.0
    if distance > tolerance:
        return 0.0
    return 1.0 - 0.5 * (distance / tolerance)


def reinforced_confidence(
    base_confidence: float,
    correct_count: int,
) -> float:
    """Boost base confidence using accumulated correct confirmations.

    Each confirmation adds REINFORCEMENT_BOOST_PER_CONFIRM (0.05) to the base
    confidence, up to a maximum total boost of REINFORCEMENT_BOOST_CAP (0.4).
    The result is capped at 1.0.  Zero or negative base confidence is unchanged.
    """
    if base_confidence <= 0.0 or correct_count <= 0:
        return base_confidence
    boost = min(correct_count * REINFORCEMENT_BOOST_PER_CONFIRM, REINFORCEMENT_BOOST_CAP)
    return min(base_confidence + boost, 1.0)


def compute_spread(values: list[float]) -> float:
    """Population standard deviation of *values*.

    Returns 0.0 for empty or single-element lists.
    """
    n = len(values)
    if n <= 1:
        return 0.0
    mean = sum(values) / n
    return math.sqrt(sum((v - mean) ** 2 for v in values) / n)


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


# -- Phase 2 legacy (used only for v2→v3 migration) ---------------------

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
        return asdict(self)


# -- Phase 3 location model ---------------------------------------------

@dataclass(frozen=True)
class LocationModel:
    location_id: str
    label: str
    prototype: float
    observation_values: tuple[float, ...]
    observation_count: int
    spread: float
    guess_count: int
    correct_count: int
    incorrect_count: int
    first_seen_at: str
    last_seen_at: str

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "LocationModel":
        raw_values = payload.get("observation_values", [])
        values = tuple(float(v) for v in raw_values)  # type: ignore[union-attr]
        return cls(
            location_id=str(payload["location_id"]),
            label=str(payload["label"]),
            prototype=float(payload["prototype"]),
            observation_values=values,
            observation_count=int(payload["observation_count"]),
            spread=float(payload["spread"]),
            guess_count=int(payload["guess_count"]),
            correct_count=int(payload["correct_count"]),
            incorrect_count=int(payload["incorrect_count"]),
            first_seen_at=str(payload["first_seen_at"]),
            last_seen_at=str(payload["last_seen_at"]),
        )

    def to_dict(self) -> dict[str, object]:
        d = asdict(self)
        d["observation_values"] = list(d["observation_values"])
        return d

    def with_merged_observation(self, value: float) -> "LocationModel":
        new_values = self.observation_values + (value,)
        new_count = self.observation_count + 1
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

    @classmethod
    def from_record(cls, record: LocationRecord) -> "LocationModel":
        return cls(
            location_id=record.location_id,
            label=record.label,
            prototype=record.observation_value,
            observation_values=(record.observation_value,),
            observation_count=record.observation_count,
            spread=0.0,
            guess_count=record.guess_count,
            correct_count=record.correct_count,
            incorrect_count=record.incorrect_count,
            first_seen_at=record.first_seen_at,
            last_seen_at=record.last_seen_at,
        )
