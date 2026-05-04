# Changelog

## Release Phase R2 - Core SDK Extraction & Public API (Completed 2026-04-30)

- TestPyPI smoke test passed 2026-05-03: `pip install tot-agent==0.7.0rc1` from TestPyPI succeeded in a clean venv; `tot --help` and `python -c "from location_agent import Agent, __version__; print(__version__)"` both returned correctly. Package name reserved; R3 now active.
- Bumped package version to `0.7.0rc1` and locked the public surface in `location_agent.__all__`: `Agent`, `LearnResult`, `RecognitionResult`, `MemoryStorage`, `MemoryStore`, `LocalJSONStore`, `EventLogger`, `SensorAdapter`, `ImageAdapter`, `ObservationBundle`, `RegionDescriptor`, `load_adapters`, `SessionController`, exception classes (`ObservationError`, `LabelNameError`, `SensorObservationError`, `LabelConflictError`, `LabelLookupError`), and `__version__`.
- Added `Agent` facade in `src/location_agent/agent.py` wrapping `MemoryStore` + `EventLogger` + adapter discovery; exposes `learn_scalar`, `recognize_scalar`, `confirm_scalar`, `correct_scalar`, `sense`, `learn_sensor`, `inspect`, `reset` plus frozen `LearnResult` / `RecognitionResult` dataclasses.
- Added `MemoryStorage` `typing.Protocol` (runtime-checkable) in `src/location_agent/storage.py`; `LocalJSONStore` is the public alias for the concrete `MemoryStore`.
- Added `_internal/` package with `FirestoreStore` stub (R3) and `_deprecation.deprecated()` helper.
- Added sensor-adapter plugin discovery in `src/location_agent/plugins.py` (`load_adapters()`) backed by the `tot.adapters` entry-point group; registered the built-in `image = "location_agent.models:ImageAdapter"` in `pyproject.toml`.
- Added `examples/example-adapter/` reference package demonstrating third-party adapter registration.
- Published JSON Schemas under `schemas/`: `observation_bundle.schema.json` and `runtime_memory.v7.schema.json`. New `tests/test_schemas.py` validates a live-built bundle and a live runtime memory snapshot.
- Cleared all 35 mypy errors. CI now gates on `mypy --strict src/location_agent` (removed `continue-on-error: true`).
- Added `tests/test_public_api.py` (asserts `__all__` shape, importability, docstrings, runtime-checkable Protocol), `tests/test_agent_facade.py` (teach → recognize → inspect via `from location_agent import Agent`), `tests/test_plugin_discovery.py` (entry-point discovery with happy path, non-adapter rejection, load failure handling, empty group).
- Added `docs/api.md` (SemVer policy, public/internal split, `SessionController` carve-out) and `docs/plugins.md` (adapter contract, threat model). Added SDK Quickstart section to `README.md`.
- Added `jsonschema>=4.21` to `[project.optional-dependencies] dev`.
- Verified: 197 tests pass; `mypy --strict src/location_agent` clean across 13 source files; coverage ≥ 80%.

## Release Phase R1 - Productization Foundation (Completed 2026-04-29)

- Adopted `src/` layout: `location_agent/` → `src/location_agent/`.
- Authored `pyproject.toml` (PEP 621) with hatchling backend, `tot` console script, and `[dev]` extras (pytest, pytest-cov, ruff, mypy, pre-commit, pip-audit, build).
- Added `__main__.py` so `python -m location_agent` invokes the CLI.
- Added `--version` / `-V` flag to the CLI.
- Added Apache-2.0 `LICENSE`, `SECURITY.md` (private vulnerability reporting), `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1), `.editorconfig`, `.pre-commit-config.yaml`.
- Added GitHub Actions workflows: `ci.yml` (ruff, ruff format, mypy advisory, pytest matrix on Ubuntu/macOS/Windows × Python 3.10/3.11/3.12 with coverage gate ≥ 80%, pip-audit), `codeql.yml` (weekly Python analysis), `publish-testpypi.yml` (manual / `v*-rc*` tag triggered, OIDC trusted publishing).
- Added `.github/dependabot.yml` for weekly pip + GitHub Actions dependency updates.
- Added issue templates (bug, feature) and PR template referencing both research and release phase tracks.
- Configured `ruff` (E/W/F/I/B/UP/SIM/RUF select; ignored RUF005, RUF059 pending R2 cleanup) and `mypy` (advisory in R1, gating in R2).
- Verified: `pip install -e \".[dev]\"` succeeds; `tot --version` prints `tot-agent 0.6.0`; full 177-test suite passes; coverage = 82%; `ruff check .` and `ruff format --check .` clean; `python -m build` produces sdist + wheel that pass `twine check`.
- Bumped package version to `0.6.0`.

## Phase 8 - Modality-Neutral Observation Bundle

- Accepted Phase 7 after validating exact-fingerprint sensor preview with 153 passing tests and manual quiet-mode smoke run.
- Bumped runtime schema from `6` to `7` to add `observation_bundles` collection for persisting normalized bundles.
- Added `ObservationBundle` frozen dataclass with all Perception Architecture Contract fields: `bundle_id`, `timestamp`, `adapter_id`, `modality`, `reference_frame`, `pose_estimate`, `motion_estimate`, `sensor_origin`, `regions`, `primitive_features`, `concept_candidates`, `raw_refs`, `provenance`.
- Added `RegionDescriptor` frozen dataclass for spatial region descriptors within bundles.
- Added `SensorAdapter` abstract base class defining the adapter contract: `adapter_id`, `modality`, and `observe()`.
- Added `ImageAdapter` implementing `SensorAdapter`, wrapping Phase 7's `SensorObservation` SHA-256 flow into `ObservationBundle` shape while preserving fingerprint-based recognition for backward compatibility.
- Added `ImageAdapter.fingerprint_from_bundle()` and `sensor_observation_from_bundle()` for legacy binding interop.
- Added `MemoryStore.store_bundle()`, `get_bundle()`, and `bind_sensor_bundle()` for bundle persistence and combined bundle+binding creation.
- Added v6→v7 schema migration that adds `observation_bundles={}` without altering existing data.
- Rewired session `_handle_sensor_input()` to route through `ImageAdapter.observe()` → `ObservationBundle` → learning, with `bundle_id` and `adapter_id` logged in all event entries.
- Extended `EventLogger.log()` with `bundle_id` and `adapter_id` optional parameters.
- Updated session banner and help text to Phase 8: Modality-Neutral Observation Bundle.
- Created `media/scenarios/phase_08_observation_bundle_contract.json` with 6 validation steps.
- Updated `media/catalog.json` to reference `phase_08_observation_bundle_contract` on bedroom scene asset.
- Expanded the automated suite to 177 tests (24 new), including bundle field validation, adapter normalization, cross-adapter shape invariants, bundle persistence, v6→v7 migration, and same-shape verification between ImageAdapter and MockAudioAdapter.

## Phase 7 - Exact-Fingerprint Sensor Preview

- Accepted Phase 6 after validating typed concept nodes, relation enforcement, concept CRUD, and 146 passing tests.
- Added temporary-preview docstrings to `SensorObservation` and `SensorBinding` documenting that SHA-256 fingerprint recognition is a Phase 7 baseline replaced by content-based `ObservationBundle` normalization in Phase 8.
- Added temporary-preview note to the interactive session banner for the `sense` command.
- Updated session phase number and title to Phase 7: Exact-Fingerprint Sensor Preview.
- Added 3 new memory-layer sensor regression tests: multi-binding persistence, binding update to different location, and provenance verification.
- Added 4 new session-layer sensor regression tests: multi-image learn/recognize, wrong-guess correction, unknown-image label prompting, and multiple images to same location.
- Created `media/scenarios/phase_07_sensor_preview_regression.json` with 5 regression steps covering learn, recognize, correct, multi-bind, and unknown flows.
- Updated `media/catalog.json` to reference `phase_07_sensor_preview_regression` on relevant assets.

## Phase 6 - Structured Graph and Concept Scaffold

- Accepted Phase 5 after validating cycle detection, context command, and 123 passing tests.
- Bumped runtime schema from `5` to `6` to add `concept_kind` field on `ConceptNode`.
- Added `VALID_CONCEPT_KINDS` (primitive, composite, scene_hypothesis, named) and `VALID_RELATION_RULES` mapping relation kinds to valid source/target type pairs.
- Added `validate_relation()` function that enforces allowed relation kind + node type pairs at the storage layer.
- Added typed concept CRUD to `MemoryStore`: `create_concept()`, `lookup_concept_by_name()`, `alias_concept()`, `link_concepts()`, `concept_relations()`, `inspect_concepts()`.
- Added v5→v6 schema migration that backfills `concept_kind="named"` on existing concept nodes.
- Added `concept`, `relate`, and `concepts` CLI commands to the interactive session loop.
- Relation validation rejects invalid kind+type pairs (e.g., `contains` between concepts is rejected).
- Concept creation is idempotent — creating a concept that already exists returns the existing node.
- Link deduplication works for concept-to-concept edges (same source/target/kind returns existing edge).
- Updated the session banner, help text, and prompt properties for Phase 6 commands.
- Expanded the automated suite to 146 tests, including concept CRUD, relation validation, concept persistence across reload, alias lookup, link deduplication, self-link rejection, bidirectional relation queries, CLI integration for concept/relate/concepts commands, and invalid kind rejection.

## Phase 5 - Nested Location Context

- Accepted Phase 4 after a refreshed quiet-mode manual smoke run covering learned-span inference, rename, alias, and `sense /path/to/file` recognition.
- Promoted Phase 5 to the active implementation target across the continuity docs and project-state artifacts.
- Updated the interactive session banner and help text to Phase 5: Nested Location Context.
- Added explicit `contain` and `overlap` commands to the session loop.
- Added relation-aware no-op handling so duplicate relations and self-links do not create graph edges.
- Made overlap relations canonical and undirected in storage while keeping containment directional as `parent -> child`.
- Extended active-context derivation and operator feedback so enclosing or overlapping context is surfaced after successful recognition when relevant.
- Extended `inspect` output in both verbose and quiet mode to include active context plus `contains`, `within`, and `overlaps` summaries.
- Added a committed `phase05_house_scene.png` fixture, updated `media/catalog.json`, and added `media/scenarios/phase_05_nested_context_walk.json`.
- Added containment cycle detection: `link_locations()` raises `ValueError` when a proposed containment edge would create a direct or transitive cycle.
- Added on-demand `context` CLI command that queries and displays active context for any named location without requiring a recognition event.
- Expanded the automated suite to 123 tests, including cycle detection (direct and transitive), context command tests, overlap validation, containment persistence, overlap deduplication, alias-based relation lookup, relation-aware inspect output, active-context emission, and explicit Phase 5 media manifest coverage.

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
- Added a repo-local media ladder with committed Phase 4 PNG fixtures, `media/catalog.json`, and ordered scenario manifests in `media/scenarios/`.
- Added `MEDIA_PLAN.md` plus roadmap and current-phase documentation that require every future phase to name its media pack and validation scenario.
- Replanned all pending work after Phase 4 so Phases 6-10 remain perception-first while Phases 11-28 converge on a synthetic memory-and-attention engine built around `ObservationBundle`, `ExperienceFrame`, `MemoryUnit`, activation competition, replay, resurfacing, reconsolidation, and body-relative context.
- Extended `inspect` output to show canonical label, aliases, label id, and rename history count.
- Wrong-guess corrections now rename the label while preserving the old canonical name as an alias.
- Event logging now records scalar-vs-sensor observation kind plus file fingerprint metadata for sensor inputs.
- Expanded the automated suite to 105 tests, including media manifest validation, committed-fixture sensor smoke coverage, label reuse, span-aware recognition, nested context, concept attachment, sensor recognition, provenance, and migration coverage.

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
