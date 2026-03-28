# Validation

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
