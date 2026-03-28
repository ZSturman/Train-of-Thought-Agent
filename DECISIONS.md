# Decisions

## Phase 1 - 2026-03-26

### Decision: Use standard-library-only Python for the first implementation

- Rationale: The environment already has Python 3.12.4, and Phase 1 should stay runnable and inspectable without dependency installation.
- Alternatives considered: Adding a packaging toolchain or third-party persistence utilities
- Consequences: The implementation stays small and portable, but convenience features from external libraries are deferred.

### Decision: Normalize grayscale observations to six decimal places before lookup and persistence

- Rationale: Raw float equality is brittle, and a fixed normalized key gives deterministic exact matching for Phase 1.
- Alternatives considered: Raw float storage, decimal strings without normalization, binary float hashing
- Consequences: `0.25` and `0.250000` resolve to the same observation key, while tolerance-based matching is deferred to Phase 2.

### Decision: Keep exactly one mutable location record per normalized observation key in Phase 1

- Rationale: The simplest inspectable memory model is one observation key mapped to one current label with explicit correction history in logs.
- Alternatives considered: Multiple candidate labels per observation, confidence-ranked alternatives, separate correction tables
- Consequences: Wrong guesses are corrected by mutating the existing record instead of adding competing records.

### Decision: Keep labels as plain strings until Phase 4

- Rationale: Phase 1 needs working behavior quickly, and first-class label graphs would be premature complexity.
- Alternatives considered: Immediate label nodes and graph edges
- Consequences: Phase 4 will need an explicit migration from string labels to label nodes.

### Decision: Treat root tracking artifacts as the authoritative continuity state

- Rationale: Future iterations need continuity that does not depend on chat history alone.
- Alternatives considered: Treating runtime memory as the sole source of truth, relying on conversational context
- Consequences: Any future conflict between chat and project files must be repaired in the smallest consistent way and documented in these artifacts.

### Decision: Keep learned runtime state in `runtime/` and tracking state at the project root

- Rationale: The project needs a clean separation between descriptive continuity artifacts and mutable learned experience.
- Alternatives considered: Storing learned memory inside the tracking files, mixing runtime data and planning state in one JSON document
- Consequences: Future phases can migrate runtime memory separately while preserving stable planning continuity files.

### Decision: Log human-supplied labels for unknown observations as explicit feedback events

- Rationale: Phase 1 requires every observation cycle to log observation, decision, confidence, feedback, and memory mutation, even when no guess is made.
- Alternatives considered: Logging only decision and mutation for unknown observations
- Consequences: The event log captures both the ask-for-label decision and the user's label response before the corresponding memory mutation.
