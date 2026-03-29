# TODO

## Immediate Tasks

- Decide whether to accept Phase 4 after manual validation
- Fill the final Phase 4 disposition in `VALIDATION.md`

## Tasks Needed Before Phase Completion

- Review whether duplicate-label migration disambiguation needs a more explicit user-facing policy
- Decide whether no-op rename/alias commands should stay silent or be logged
- Record a refreshed manual smoke sequence that covers label reuse and `sense /path/to/file`

## Next Phase Tasks

- Begin Phase 5: Nested Location Context
- Build CLI-facing workflows for teaching containment and overlap relations
- Expand active-context inspection so parent and overlapping locations remain visible during movement
- Prepare Phase 6 concept-node commands and validation hooks before entity work begins

## Deferred Improvements

- Add richer inspection tooling for rename history details
- Consider richer span models for non-convex locations instead of relying only on inclusive min/max bounds
- Consider indexed nearest-neighbor lookup when model counts grow
- Consider richer sensor fingerprints for near-duplicate media rather than exact file matches only
- Consider explicit ambiguity handling when shared labels become in-scope

## Technical Debt

- Runtime persistence is still single-writer JSON and JSONL only
- CLI interaction remains intentionally synchronous and line-oriented
- Name resolution and graph traversal are rebuilt by scanning in-memory structures
- Duplicate v3 labels are auto-suffixed during migration; that policy may need a dedicated UX later

## Research Questions

- When overlapping or contextual labels arrive, should ambiguity be resolved by ranked candidates or explicit clarification prompts?
- Should alias lookup remain case-insensitive once richer language-like labels appear?
- How should label, concept, and future entity nodes share graph-edge semantics without overfitting the ontology too early?
