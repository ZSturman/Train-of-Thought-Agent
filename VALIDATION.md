# Validation

## Phase 2 - Noisy Scalar Matching and Confidence Calibration

- Status: in-progress

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
