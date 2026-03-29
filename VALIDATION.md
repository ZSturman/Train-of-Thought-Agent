# Validation

## Phase 4 - First-Class Labels

- Status: pending

### What was tested

- Automated suite via `python3 -B -m unittest discover -s tests -v`
- Manual quiet-mode smoke run in a temporary runtime directory:
  - learn `0.25 -> kitchen`
  - reuse `kitchen` for a later observation and verify it reinforces the same location
  - rename `kitchen -> break room`
  - bind a sensor input path to `break room`
  - add alias `galley`
  - inspect
  - verify persisted `schema_version: 5`, one location model, one label node, canonical `break room`, aliases `kitchen, galley`, plus graph/evidence scaffolding
- Models:
  - `LabelNode` serialization, alias addition, canonical rename, alias promotion
  - `LocationModel` serialization, empty sensor-first locations, and merge behavior after the `label_id` migration
- Memory store:
  - blank bootstrap with `location_models`, `label_nodes`, `graph_edges`, `sensor_bindings`, and `evidence_records`
  - learn-and-reload with label node creation
  - label reuse reinforcement
  - nested location context edges
  - concept-node attachment
  - sensor binding and re-recognition
  - provenance-only evidence (`user` or `sensor`)
  - lookup by canonical name and alias
  - rename flow, alias flow, conflict rejection
  - v1 -> v5, v2 -> v5, v3 -> v5, and v4 -> v5 migration
  - duplicate v3 label disambiguation during migration
- Session:
  - correct guess merge flow
  - existing-label reinforcement flow (`Point one`)
  - learned-span default inference flow (`0.10`, `0.30`, then `0.28`)
  - wrong guess correction becoming canonical rename plus alias preservation
  - `sense /path/to/file` learning and recognition flow
  - `rename` command
  - `alias` command
  - richer `inspect`
  - reset flow and event logging
- Stress:
  - 1000 unique learned observations persist and reload
  - noisy-query classification still behaves correctly
  - 100 models × 10 merges each still behaves correctly

### What passed

- All 101 automated tests passed
- Phase 1-3 confidence, merge, reset, and stress behavior still passed after the label-node refactor
- New location-first tests passed for label reuse, learned-span inference, nested context, concept attachment, sensor recognition, provenance, and v5 migration scaffolding

### What failed

- No automated test failures

### Edge cases

- Active canonical names and aliases are globally unique across label nodes
- Reusing an existing label now reinforces that same learned location instead of creating a naming conflict
- If a location has confirmed scalar observations across a wider range, values inside that learned span are matched to it by default unless conflicting evidence appears
- Rename preserves the old canonical name as an alias by default
- Alias lookup is case-insensitive while preserving stored casing
- Duplicate v3 labels are disambiguated deterministically during migration as `name`, `name (2)`, `name (3)`, ...
- Wrong-guess correction keeps the location model and label node identity while changing the canonical label
- Sensor recognition uses direct file fingerprints only; no LLM-derived facts are persisted

### Stress tests or benchmarks

- `merge_stress_duration_seconds=7.981283`
- `noisy_stress_duration_seconds=0.011273`
- `stress_duration_seconds=33.427336`

### Unresolved issues

- A refreshed manual CLI smoke validation covering the learned-span flow has not been recorded yet
- Runtime persistence remains single-writer JSON and JSONL only
- Nearest-neighbor search is still a linear scan over all scalar-backed location models
- Shared labels across multiple distinct locations remain out of scope until the later ambiguity phase

### Disposition

- pending

## Phase 3 - Multi-Observation Location Models

- Status: accepted
- Disposition: accepted
- Notes:
  - Phase 3 was accepted before Phase 4 implementation started.
  - Its automated behaviors remain covered by the Phase 4 regression suite.

## Phase 2 - Noisy Scalar Matching and Confidence Calibration

- Status: accepted
- Disposition: accepted

## Phase 1 - Persistent Grayscale Location Bootstrap

- Status: accepted
- Disposition: accepted
