# TODO

## Immediate Tasks

- Run manual CLI smoke test for Phase 3 and validate
- Accept or revise Phase 3 based on validation results

## Tasks Needed Before Phase Completion

- Manual CLI smoke sequence: learn a value, re-enter with noise, confirm merge, run `inspect`, verify prototype shift
- Verify schema v2 → v3 migration by running against existing runtime/location_memory.json
- Fill VALIDATION.md disposition for Phase 3

## Next Phase Tasks

- Promote labels from plain strings to first-class label nodes (Phase 4)
- Design label graph with edges for proximity, correction, and co-occurrence
- Add label inspection and graph query tooling

## Deferred Improvements

- Add richer inspection tooling after the core memory loop stabilizes
- Consider replacing linear confidence decay with a more sophisticated function
- Consider adaptive tolerance per-location based on observation spread
- Compact raw observation values after N observations to control memory growth

## Technical Debt

- Runtime persistence is single-writer JSON and JSONL only
- CLI interaction is intentionally simple and synchronous
- Nearest-neighbor search is linear scan over all model prototypes (fine for < 1000 models)
- `LocationRecord` kept in models.py only for migration; can be removed once v2 files are extinct

## Research Questions

- Should tolerance become adaptive per-model based on the model's spread?
- How should label nodes relate to each other in the Phase 4 graph?
- Should future ambiguity prompts show ranked candidate models?
