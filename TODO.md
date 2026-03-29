# TODO

## Immediate Tasks

- Run manual CLI smoke test for Phase 2 and validate
- Accept or revise Phase 2 based on validation results

## Tasks Needed Before Phase Completion

- Manual CLI smoke sequence: learn a value, re-enter with noise, verify graded confidence
- Verify schema v1 → v2 migration by running against existing runtime/location_memory.json
- Fill VALIDATION.md with Phase 2 results

## Next Phase Tasks

- Design observation aggregation so repeated nearby observations merge into one location model
- Decide prototype update rule (running mean, weighted mean, etc.)
- Add outlier handling for observations that are close but clearly wrong
- Add model inspection tooling (show merged prototype statistics)

## Deferred Improvements

- Promote labels to first-class nodes in Phase 4
- Add richer inspection tooling after the core memory loop stabilizes
- Add schema migration helpers before the first structural runtime migration
- Consider replacing linear confidence decay with a more sophisticated function if calibration tests reveal issues

## Technical Debt

- Runtime persistence is single-writer JSON and JSONL only
- No schema migration layer yet beyond explicit version fields and inline migration logic
- CLI interaction is intentionally simple and synchronous
- Nearest-neighbor search is linear scan over all stored observations (fine for < 1000 entries)

## Research Questions

- What prototype update rule should Phase 3 use for observation aggregation?
- How should future ambiguity prompts balance caution and usability?
- Should tolerance be adaptive per-location based on observation spread?
