# Changelog

## Phase 4 - First-Class Labels

- Bumped runtime schema from `4` to `5` to add pre-entity location graph scaffolding, sensor bindings, and provenance-aware evidence records.
- Added `LabelNode` and `RenameRecord` models.
- Replaced inline `LocationModel.label` storage with `LocationModel.label_id`.
- Added top-level `label_nodes` persistence and case-insensitive name resolution across canonical names and aliases.
- Implemented chained migrations through `schema_version: 5`, including v4 -> v5 scaffolding upgrades.
- Added deterministic duplicate-label disambiguation during migration (`name`, `name (2)`, ...).
- Added label-aware memory APIs for lookup, rename, alias creation, and inspect snapshots.
- Reused location labels now reinforce the existing location model instead of throwing a naming error during learning.
- Scalar recognition now treats the confirmed observation range for one location as an inclusive learned span, so values like `0.28` default to a location already confirmed at `0.10` and `0.30`.
- Added empty sensor-first location support so file-backed observations can create or reinforce locations without inventing scalar values.
- Added `ConceptNode`, `GraphEdge`, `SensorBinding`, and `EvidenceRecord` models for location hierarchy, concept scaffolding, and provenance tracking.
- Added interactive `rename` and `alias` commands to the session loop.
- Added interactive `sense /path/to/file` handling for simulated sensor recognition from direct file fingerprints.
- Extended `inspect` output to show canonical label, aliases, label id, and rename history count.
- Wrong-guess corrections now rename the label while preserving the old canonical name as an alias.
- Event logging now records scalar-vs-sensor observation kind plus file fingerprint metadata for sensor inputs.
- Expanded the automated suite to 101 tests, including label reuse, span-aware recognition, nested context, concept attachment, sensor recognition, provenance, and migration coverage.

## Phase 3 - Multi-Observation Location Models

- Replaced one-record-per-observation storage with `LocationModel` dataclass: each
  model holds a running-mean prototype, all raw observation values, and population
  standard deviation (spread).
- Storage key changed from observation key string to UUID `location_id`.
- Confirming a noisy guess now merges the observation value into the matched model,
  shifting the prototype and updating spread.
- Added outlier detection: observations farther than 3× max(spread, tolerance) from
  the model prototype trigger a warning before merging.
- Added `inspect` CLI command to display all stored models with prototype, observation
  count, and spread.
- Implemented transparent schema v2 -> v3 migration on load, converting each
  `LocationRecord` in `locations_by_observation` to a `LocationModel` in
  `location_models`.

## 2026-03-28

- Implemented Phase 2: Noisy Scalar Matching and Confidence Calibration.
- Added distance-based confidence model with linear decay within configurable
  tolerance (default 0.05), replacing binary exact-match confidence from Phase 1.

## 2026-03-26

- Bootstrapped continuity artifacts for the long-horizon project.
- Implemented Phase 1 with stdlib-only persistence, event logging, and an
  interactive CLI loop.
