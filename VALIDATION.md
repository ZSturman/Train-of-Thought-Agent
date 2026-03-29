# Validation

## Phase 3 - Multi-Observation Location Models

- Status: pending

### What was tested

- Automated unit, regression, and stress suite via `python3 -m pytest tests/ -v`
- Model math: compute_spread, LocationModel creation, serialization round-trip, with_merged_observation (2/5/10 merges), immutability, from_record conversion
- Merge behavior: merge shifts prototype, confidence computed against shifted prototype
- Outlier detection: single-observation model uses tolerance as floor, tight-spread model detects outlier
- Memory store: blank bootstrap with location_models, find_nearest against prototypes, learn-and-reload via lookup_by_id, inspect_models
- Schema migration: v2→v3 structural migration, v1→v3 chained migration
- Session: correct guess with merge, noisy merge shifts prototype, repeated confirmations shift progressively, inspect command, merge event logging, outlier/collision paths
- Stress: 1000 unique observations, 100 observations with noisy queries, 100 models × 10 merges each

### What passed

- All 64 automated tests passed
- Phase 1+2 regression tests adapted and passing (memory, session, confidence)
- New Phase 3 tests pass (14 model, 2 merge/outlier confidence, 4 memory/migration/inspect, 5 session merge/inspect/event, 1 merge stress)

### What failed

- No automated test failures

### Edge cases

- All Phase 1+2 edge cases still covered
- Single-observation model has spread=0; outlier detection uses tolerance as floor
- Merge recomputes prototype as exact arithmetic mean of all stored observation values
- LocationModel is frozen/immutable; with_merged_observation returns a new instance
- Chained migration: v1 files migrate through v2 policy update then v3 structural conversion
- Inspect on empty store returns empty list
- Near-collision guard uses model prototype (not observation key) for distance check

### Stress tests or benchmarks

- 1000-observation learn+reload stress test passes
- 100-observation noisy-query classification stress test passes
- 100 models × 10 merges stress test passes

### Unresolved issues

- Labels are still plain strings rather than first-class nodes (Phase 4)
- Runtime persistence remains single-writer JSON and JSONL only
- Nearest-neighbor search is linear scan over all model prototypes (sufficient for current scale)
- Outlier detection warns but does not block — user can always confirm

### Disposition

- pending

## Phase 2 - Noisy Scalar Matching and Confidence Calibration

- Status: accepted

### What was tested

- Automated unit, regression, and stress suite via `python3 -m pytest tests/ -v`
- Distance and confidence math: scalar_distance, distance_to_confidence
- find_nearest: exact match, within-tolerance, beyond-tolerance, nearest-wins, equidistant tiebreak
- Near-collision detection for close observations
- Phase 1 backward compatibility: blank bootstrap, learn-and-reload, normalized lookup
- Session: exact match guess, noisy match guess, far-observation unknown, uncertain guess rejection, near-collision guard confirm/skip, invalid inputs and wrong-guess correction, yes/no feedback, verbose banner and summary
- Stress: 1000 unique observations persist and reload, 100 observations with noisy queries classify correctly

### What passed

- All 30 automated tests passed
- Phase 1 regression tests pass (3 memory, 4 session adapted for Phase 2)
- New Phase 2 tests pass (16 confidence, 5 session, 1 stress)

### What failed

- No automated test failures

### Edge cases

- All Phase 1 edge cases still covered (empty input, non-numeric, out-of-range, empty label, invalid feedback, same normalized key)
- Observation within tolerance of learned value produces graded confidence < 1.0
- Observation at tolerance boundary produces confidence at floor (0.5)
- Observation beyond tolerance produces confidence 0.0
- Uncertain guess (confidence between 0 and threshold) shows best guess with uncertainty
- Uncertain guess rejected → learns new label with collision guard
- Near-collision guard: user can confirm or skip learning a near-duplicate
- Schema v1 memory files migrated transparently to v2 on load

### Stress tests or benchmarks

- 1000-observation exact-match stress test passes
- 100-observation noisy-query stress test validates correct classification rates

### Unresolved issues

- Matching is distance-based but does not aggregate repeated observations into location models
- Labels are still plain strings rather than first-class nodes
- Runtime persistence remains single-writer JSON and JSONL only
- Nearest-neighbor search is linear scan (sufficient for current scale)

### Disposition

- pending

## Phase 1 - Persistent Grayscale Location Bootstrap

- Status: accepted

### What was tested

- Automated unit, regression, and stress suite via `python3 -m unittest discover -s tests -v`
- Blank memory bootstrap behavior for an empty file
- Learn and reload persistence across store restarts
- Normalization regression for `0.25` and `0.250000`
- Invalid observation, empty label, and invalid feedback reprompts
- Wrong-guess correction updating the existing observation record
- Manual CLI smoke sequence using `python3 -m location_agent.cli`

### What passed

- All 6 automated tests passed
- Stress validation learned 1000 unique normalized observations, reloaded the store, and resolved sample lookups correctly
- Manual smoke sequence passed:
  - `0.333333` learned as `office`
  - repeated `0.333333` guessed `office` with confidence `1.00`
  - runtime memory and event logs updated as expected
- Event logging covered observation, decision, feedback, session lifecycle, and memory mutation events

### What failed

- No automated test failures
- No manual smoke failures

### Edge cases

- Empty observation input rejected
- Non-numeric observation rejected
- Out-of-range observation rejected
- Empty label rejected and reprompted
- Invalid feedback rejected and reprompted
- Same normalized value entered with different string precision resolves to one observation key
- Wrong guess correction updates one existing record instead of creating a duplicate

### Stress tests or benchmarks

- Automated stress test duration: `2.549653` seconds for 1000 unique learned observations plus reload and sample lookup verification
- No schema corruption or lookup failures observed during the stress run

### Unresolved issues

- Matching remains exact and does not tolerate noise yet
- Labels are still plain strings rather than first-class nodes
- Runtime persistence remains single-writer JSON and JSONL only

### Disposition

- accepted
