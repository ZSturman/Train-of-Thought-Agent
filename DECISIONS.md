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

## Phase 2 - 2026-03-28

### Decision: Use linear confidence decay with tolerance of 0.05

- Rationale: 5% of the unit range provides meaningful noise tolerance while keeping distinct locations separable. Linear decay from 1.0 (distance=0) to 0.5 (distance=tolerance) is simple, interpretable, and avoids magic numbers of Gaussian kernels.
- Alternatives considered: Gaussian kernel, step function, exponential decay, tolerance of 0.01 or 0.10
- Consequences: Observations within 0.05 of a learned value produce graded confidence. The function can be replaced with a more sophisticated model later without changing the interface.

### Decision: Lower guess threshold from 1.0 to 0.6

- Rationale: With distance-based matching, confidence < 1.0 is normal for noisy observations. A threshold of 0.6 allows confident-enough noisy matches while filtering weak ones. Must be above the floor (0.5 at tolerance boundary) to prevent low-quality guesses.
- Alternatives considered: 0.5 (too aggressive — boundary matches would guess), 0.8 (too conservative — only very close matches)
- Consequences: Guesses fire for observations within roughly 80% of tolerance. Values between 0 and 0.6 confidence trigger the new uncertain-guess path.

### Decision: Add an uncertain-guess path for low-confidence matches

- Rationale: When confidence is between 0 and the threshold, the agent has a plausible match but isn't confident enough to commit. Showing the best guess with uncertainty and asking for explicit confirmation prevents silent false positives while remaining helpful.
- Alternatives considered: Treating all sub-threshold matches as completely unknown, showing ranked candidates
- Consequences: Users see the agent's reasoning even when it's unsure. Ranked candidates deferred to Phase 3+.

### Decision: Add a near-collision guard when learning new observations

- Rationale: Without a guard, a user could teach 0.250 → kitchen and 0.252 → bathroom, creating nearly-identical observations with contradictory labels. The guard surfaces this as a confirmation prompt.
- Alternatives considered: Silently merging into the nearest existing record, blocking near-duplicate learning entirely
- Consequences: Users can still learn close observations if they explicitly confirm, but accidental duplicates are caught.

### Decision: Migrate schema v1 to v2 transparently on load (policy-only)

- Rationale: The only structural difference between v1 and v2 is the confidence_policy (added `tolerance`, changed `kind` to `distance`, lowered `guess_threshold`). No data migration is needed.
- Alternatives considered: Requiring manual migration, refusing to load v1 files
- Consequences: Existing v1 runtime files are upgraded automatically on first load. Old installations continue working without manual intervention.

## Phase 3

### Decision: Use running arithmetic mean as the prototype update rule

- Rationale: Simple, deterministic, and easy to verify. Each model stores all raw observation values and recomputes the mean on merge. No tuning parameters needed.
- Alternatives considered: Exponential moving average (recency bias not needed yet), weighted mean by confidence, median
- Consequences: Prototype converges to the true center of observations. All raw values are stored to support future alternative aggregation rules.

### Decision: Use population standard deviation for spread

- Rationale: Provides a natural measure of observation consistency that is directly comparable to tolerance. Computed from stored observation values via `compute_spread()`.
- Alternatives considered: Sample standard deviation (N-1), interquartile range, max-min range
- Consequences: Single-observation models have spread=0, which is correctly handled by using tolerance as a floor in outlier detection.

### Decision: Set outlier factor to 3× max(spread, tolerance)

- Rationale: Flags observations that are implausibly far from the current prototype. Using `max(spread, tolerance)` ensures outlier detection works for both single-observation models (where spread=0) and multi-observation models. Factor of 3 matches common 3-sigma practice.
- Alternatives considered: Fixed absolute threshold, user-configurable per-model, 2× factor
- Consequences: Outlier warnings are conservatively tuned to avoid false alarms. Users can still confirm outlier observations.

### Decision: Key storage by location_id (UUID) instead of observation key

- Rationale: With merged models, a single model may cover many different observation values. The observation key is no longer unique per model. A UUID provides a stable, unique identifier.
- Alternatives considered: Keeping observation key as primary key with aliasing, using label as key
- Consequences: Lookup by observation value requires scanning all model prototypes (linear search, acceptable at current scale). `lookup_by_id()` provides O(1) access when the ID is known.

### Decision: Chain schema migrations (v1→v2→v3) on load

- Rationale: Each migration step is small and testable. Chaining avoids duplicating v1→v2 logic inside a monolithic v1→v3 migration.
- Alternatives considered: Direct v1→v3 jump, requiring manual migration between major versions
- Consequences: Any version of the runtime file is automatically brought to v3. Future phases add one migration step each.

### Decision: Store all raw observation values in the model

- Rationale: Enables recomputing prototype and spread with different algorithms in the future. Small memory cost at current scale.
- Alternatives considered: Storing only running statistics (mean, count, sum-of-squares), discarding raw values after N observations
- Consequences: Memory grows linearly with observation count per model. Acceptable for foreseeable scale; can be compacted later if needed.
