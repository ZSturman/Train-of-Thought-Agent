# TODO

## Immediate Tasks

- Implement `ObservationBundle` dataclass with all Perception Architecture Contract fields
- Define `SensorAdapter` protocol (base class) that sensor modules must implement
- Create `ImageAdapter` wrapping existing `SensorObservation` into `ObservationBundle` shape
- Add bundle field validation hooks and inspection tooling
- Add Phase 8 tests: bundle validation, adapter normalization invariants, two-adapter shape tests
- Create `phase_08_observation_bundle_contract.json` scenario manifest
- Decide on schema v7 bump (bundle metadata persistence)

## Tasks Needed Before Phase Completion

- Verify `sense` command routes through adapter → bundle → learning path
- Verify two mock adapters produce the same bundle shape
- Verify bundle provenance and raw references survive normalization
- Run full regression suite (153+ tests must still pass)

## Next Phase Tasks

- Draft the Phase 11 `ExperienceFrame` contract and inspection rules before any frame capture code path is added
- Draft the Phase 13 `MemoryUnit` schema and mixed-storage migration plan before the first generic memory-writing phase starts

## Deferred Improvements

- Add richer inspection tooling for rename history details
- Consider richer span models for non-convex locations instead of relying only on inclusive min/max bounds
- Consider indexed nearest-neighbor lookup when model counts grow
- Consider richer sensor fingerprints for near-duplicate media rather than exact file matches only
- Consider replacing abstract generated fixtures with richer captured scenes once later phases need stronger realism
- Consider explicit ambiguity handling when shared labels become in-scope
- Consider how replay queues and resurfacing windows should stay inspectable without flooding the operator surface

## Technical Debt

- Runtime persistence is still single-writer JSON and JSONL only
- CLI interaction remains intentionally synchronous and line-oriented
- Name resolution and graph traversal are rebuilt by scanning in-memory structures
- Duplicate v3 labels are auto-suffixed during migration; that policy may need a dedicated UX later

## Research Questions

- When overlapping or contextual labels arrive, should ambiguity be resolved by ranked candidates or explicit clarification prompts?
- Should alias lookup remain case-insensitive once richer language-like labels appear?
- How should label, concept, and future entity nodes share graph-edge semantics without overfitting the ontology too early?
- What region geometry is expressive enough for early salience and attention work without forcing a final segmentation model too soon?
- What is the minimal `reference_frame` and `sensor_origin` contract that still scales to body-relative robot sensing later?
- What is the smallest useful `ExperienceFrame` that still supports chunking, residue, and later attention scoring?
- How should `MemoryUnit` example links, compressed summaries, and reconsolidation windows be inspected without introducing many bespoke memory classes?
