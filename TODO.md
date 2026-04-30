# TODO

The active phases on each track. When a phase completes, its checklist is moved into `CHANGELOG.md` under a dated heading and replaced here with the next phase's items.

## Active Research Phase: Phase 9 — Region Descriptors & Primitive Feature Extraction

(Pending — kicks off when you give the move-on instruction for the research track. Spec lives in `PROJECT_ROADMAP.md` under "Phase 9".)

## Active Release Phase: R3 — HTTP API & Hosted Storage

**Goal:** Expose the SDK over HTTP and add a hosted memory backend (Firestore) so the upcoming web app (R4) can run against a remote instance.

### Tasks

- [ ] Define minimal REST surface (FastAPI) on top of `Agent`
  - [ ] `POST /learn` (scalar + sensor variants)
  - [ ] `POST /recognize` (scalar + sensor variants)
  - [ ] `POST /confirm`, `POST /correct`
  - [ ] `GET /inspect`, `POST /reset`
  - [ ] OpenAPI spec checked into the repo
- [ ] Concrete `FirestoreStore` implementing `MemoryStorage` (replaces the R2 stub in `_internal/firestore_store.py`); migrate to top-level public path once stable
- [ ] Auth + multi-tenant scoping
  - [ ] Decide on auth model (API key vs. OIDC); document in `docs/api.md`
  - [ ] Per-tenant memory namespacing in storage layer
- [ ] Async surface on `Agent` (or async wrapper class) for the API workers
- [ ] Deployment artifacts: Dockerfile, container CI build, sample Cloud Run / Fly.io manifest
- [ ] `tests/test_http_api.py` end-to-end against an in-memory store
- [ ] `tests/test_firestore_store.py` against the Firestore emulator
- [ ] Promote `tot-agent` to PyPI (non-rc) once R3 ships

### Dependencies / Blockers

- R2 complete (✅).
- Decision: async-first `Agent` vs. sync `Agent` + thin async wrapper. Recommendation: thin async wrapper to keep the SDK usable from synchronous notebooks.

### Acceptance Criteria

- `curl` against the running service drives teach → recognize → inspect.
- A web client can authenticate and read/write its own memory namespace.
- Firestore store passes the same Protocol contract tests as `LocalJSONStore`.
- Coverage ≥ 80%; mypy clean; CI matrix green.

### Risks / Open Questions

- Schema-evolution story for hosted memory (cannot rely on file-based migrations).
- Cost / quota model for Firestore reads when `inspect` returns the full memory.
- Whether to support both Firestore and SQLite/Postgres backends from day one.

---

## Deferred Improvements (Research Track)

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
