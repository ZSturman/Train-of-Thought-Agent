# TODO

## Immediate Tasks

- Wait for explicit user instruction before starting Phase 2
- Preserve the Phase 1 regression suite and runtime logs for future revisions
- Review Phase 1 runtime samples when re-planning or revising continuity state

## Tasks Needed Before Phase Completion

- None; Phase 1 was accepted on 2026-03-26

## Next Phase Tasks

- Define a minimal distance function for grayscale similarity
- Add confidence calibration logic for noisy matching
- Decide how low-confidence observations should trigger clarification without overguessing

## Deferred Improvements

- Promote labels to first-class nodes in Phase 4
- Merge related observations into richer location models in Phase 3
- Add richer inspection tooling after the core memory loop stabilizes
- Add schema migration helpers before the first structural runtime migration

## Technical Debt

- Runtime persistence is single-writer JSON and JSONL only
- No schema migration layer yet beyond explicit version fields
- CLI interaction is intentionally simple and synchronous
- Runtime smoke data remains in `runtime/` as a useful but manual validation trace

## Research Questions

- Is six-decimal normalization the right precision for the Phase 2 noise model?
- What confidence representation should bridge exact match and tolerant matching?
- How should future ambiguity prompts balance caution and usability?
