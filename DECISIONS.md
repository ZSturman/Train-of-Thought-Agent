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

## Phase 4 - 2026-03-28

### Decision: Use one canonical label node per location in Phase 4

- Rationale: The goal is to promote labels to first-class nodes without introducing shared-label ambiguity yet.
- Alternatives considered: Shared labels across locations immediately, multi-label locations
- Consequences: Each location owns exactly one label node for now. Shared labels are deferred to a later ambiguity-aware phase.

### Decision: Preserve old canonical names as active aliases on rename and correction

- Rationale: Users should not lose previously learned vocabulary when they refine a label.
- Alternatives considered: Storing rename history only, detaching the old name into a separate node
- Consequences: Canonical names can evolve while older names still resolve deterministically to the same location.

### Decision: Keep active canonical names and aliases globally unique

- Rationale: Phase 4 explicitly defers ambiguity handling, so name resolution must stay deterministic.
- Alternatives considered: Allowing duplicate aliases, returning multiple matches, prompting immediately on conflicts
- Consequences: Learning, rename, and alias commands reject names already owned by another label node.

### Decision: Disambiguate duplicate v3 labels during migration with numeric suffixes

- Rationale: Existing v3 memory may contain repeated plain-string labels that cannot all remain active under the new uniqueness rule.
- Alternatives considered: Failing migration, silently picking one owner, introducing shared labels early
- Consequences: Migration keeps all locations, but later duplicates become `name (2)`, `name (3)`, etc., with rename history preserving the change.

## Phase 4 Revision - 2026-03-29

### Decision: Reusing an existing location label reinforces the same location model

- Rationale: Users should be able to teach the same place with repeated observations without being forced to invent a new name. The label is not the identity; the location node is.
- Alternatives considered: Keeping hard uniqueness errors during learning, automatically creating duplicate locations with the same name
- Consequences: When a user supplies an already-known location label during learning, the observation merges into that location unless the user explicitly backs out during a conflict warning.

### Decision: Treat confirmed scalar observations as an inclusive learned span for default recognition

- Rationale: If a user confirms that `0.10` and `0.30` are both "Point one", the default behavior should be that `0.28` is probably also "Point one" unless competing evidence appears. Matching only against the running prototype throws away this stronger span signal.
- Alternatives considered: Prototype-only matching, storing spread without using it for recognition, requiring explicit user relabeling for every interior value
- Consequences: Scalar matching, near-collision checks, and outlier checks measure distance to the learned interval defined by confirmed observations rather than only to the prototype. Confidence now decays from the nearest confirmed boundary when a value falls just outside the span.

### Decision: Allow sensor-first locations with no scalar prototype

- Rationale: A file-backed sensor input can identify a location even when no grayscale observation exists yet. Creating a location without inventing a fake scalar keeps the memory grounded in direct evidence.
- Alternatives considered: Requiring a scalar observation before any sensor binding, synthesizing placeholder scalar values
- Consequences: `LocationModel.prototype` may be `None` until scalar evidence arrives. Scalar nearest-neighbor lookup skips sensor-only locations.

### Decision: Add graph and concept scaffolding before entity work

- Rationale: Nested or overlapping location context needs typed relationships and concept nodes before entities arrive. This supports later disambiguation without redesigning the storage model.
- Alternatives considered: Deferring graph edges and concept nodes until after entities, hardcoding room/building hierarchy later
- Consequences: Runtime schema v5 adds `graph_edges`, `concept_nodes`, `sensor_bindings`, and `evidence_records`, even though richer ambiguity handling remains a later phase.

### Decision: Persist provenance only from `user` or `sensor`

- Rationale: The LLM may help parse or normalize interaction, but it must never become the source of stored facts. Persisted memory must stay grounded in direct user statements or direct sensor input.
- Alternatives considered: Storing assistant-generated summaries as evidence, leaving provenance implicit
- Consequences: Nodes, edges, sensor bindings, and evidence records carry explicit provenance, and the allowed sources are limited to `user` and `sensor`.

### Decision: Seed the sensor ladder with repo-local committed image fixtures

- Rationale: The current `sense /path/to/file` flow needs deterministic assets that work offline in tests, docs, and manual smoke runs. A small committed pack keeps iteration fast while preserving a clean path to richer sensing later.
- Alternatives considered: External URLs only, generated-on-demand fixtures only, waiting until real sensor adapters exist
- Consequences: `media/catalog.json`, `media/scenarios/`, and `MEDIA_PLAN.md` become part of the continuity layer, and future phases must name their media pack and validation scenario before sensor-heavy work starts.

### Decision: Keep the media progression image-first until multimodal replay is explicitly in scope

- Rationale: Still-image fixtures are the lightest deterministic bridge between scalar-only learning and real sensor ingestion. They let the project validate stepwise sensor learning before taking on synchronization and streaming complexity.
- Alternatives considered: Introducing audio or position signals immediately, designing early phases around full multimodal bundles
- Consequences: Phase 4 through Phase 18 remain grounded in committed image-first packs, while multimodal bundles are staged for Phases 19 and 20.

### Decision: Normalize every future sensor module into one `ObservationBundle`

- Rationale: The robot end state requires modular sensor adapters without special-case learning paths per modality. A single transformed input contract keeps all downstream learning and memory modality-neutral.
- Alternatives considered: Separate per-sensor memory paths, a flat concept-token stream only, one opaque latent vector only
- Consequences: Future roadmap phases must describe how their sensing work emits `ObservationBundle` fields such as `regions`, `primitive_features`, `pose_estimate`, `motion_estimate`, and `sensor_origin`.

### Decision: Evolve concept storage into a hybrid primitive/composite graph

- Rationale: Concepts like `sky`, `grass`, `park`, and `yard` should be grounded in reusable perceptual parts, not just saved as flat names on a location. Primitive features and composite concepts need first-class storage so multiple labels can be supported from the same evidence.
- Alternatives considered: Keeping concepts as plain names only, storing only numeric embeddings without inspectable graph structure
- Consequences: Future `ConceptNode` design is planned to include kinds such as `primitive`, `composite`, `scene`, `entity`, `motion`, and `spatial`, and future `GraphEdge` relations will include part-whole, support, hypothesis, and frame-local relations.

### Decision: Treat exact-file sensor recognition as a temporary preview

- Rationale: The current `sense /path/to/file` behavior is useful for iterative progress, but the target system must match by perceptual content and reason about attended regions, motion, and body-relative spatial context.
- Alternatives considered: Treating exact-file matching as the lasting recognition model, removing the preview before a replacement exists
- Consequences: Phase 7 is explicitly documented as a temporary exact-file preview, and later phases replace file identity with region attention, content-based matching, and modality-neutral transformed bundles.

## Continuity Replan - 2026-03-30

### Decision: Preserve the location-first front of the roadmap while changing the final product target

- Rationale: The current repo has real traction in location learning, correction, and inspectable perception scaffolding. That early ladder should stay intact even though the desired end state has shifted.
- Alternatives considered: Replacing the whole roadmap from Phase 1 onward, appending a second roadmap after Phase 28
- Consequences: Phases 1 through 5 stay location-first, Phases 6 through 10 remain perception-first, and the new cognitive-engine ladder begins after the perceptual substrate is strong enough to support it.

### Decision: Reframe the long-range end state as a synthetic memory-and-attention engine

- Rationale: The desired product models how traces are written, compressed, reactivated, blocked, surfaced, and rewritten. A robot location monitor is now one application domain, not the full definition of success.
- Alternatives considered: Keeping robot monitoring as the primary end state, treating thought-like behavior as an optional add-on
- Consequences: Roadmap, media plan, validation language, and continuity notes now emphasize memory writing, activation, thresholds, replay, resurfacing, reconsolidation, and operator audit.

### Decision: Keep one generic future memory primitive instead of proliferating object classes

- Rationale: The target behavior depends more on strength, context, timing, and connectivity than on whether a trace is called an event, mood, question, or entity.
- Alternatives considered: Separate persistent classes for event memory, aggregate memory, emotion memory, thought memory, and entity memory
- Consequences: The future interface direction is documented around `ExperienceFrame`, `MemoryUnit`, `ActivationState`, `AttentionScore`, `WorkspaceState`, and `ReplayWindow`, while the current `LocationModel` and `LabelNode` remain the bootstrap substrate.

### Decision: Defer the first real cognitive schema expansion until Phase 13

- Rationale: The project should not introduce persisted generic memory traces before the perceptual and chunking substrate exists to ground them.
- Alternatives considered: Adding `MemoryUnit` persistence immediately, delaying the cognitive engine until after all robot phases
- Consequences: The current Phase 4 runtime schema remains unchanged, and the replan is implemented in the continuity layer first through roadmap, media, state, docs, and tests.

## Phase 5 - 2026-04-01

### Decision: Reject containment cycles with an error

- Rationale: Allowing `A contains B contains A` is semantically incorrect for spatial containment. The `seen` set in BFS prevents infinite loops but the stored graph should be acyclic for containment edges.
- Alternatives considered: Warning but allowing cycles, keeping them allowed silently
- Consequences: `link_locations()` raises `ValueError` if the proposed containment edge would create a cycle. Session-layer catches and emits a `cycle rejected:` message.

### Decision: Keep duplicate relation attempts silent (no audit log)

- Rationale: Duplicate relation attempts are harmless no-ops. Logging them would add noise without actionable value at current scale.
- Alternatives considered: Logging duplicate attempts as explicit no-op audit events
- Consequences: Re-teaching an existing relation emits a "no change" message to the operator but does not create an event log entry.

### Decision: Add an on-demand `context` CLI command

- Rationale: Active context was only surfaced automatically after nontrivial recognitions. A dedicated `context` command lets the user query context at any time without needing to fake a recognition event.
- Alternatives considered: Keeping context as automatic-only, surfacing context inside the `inspect` command
- Consequences: `context` prompts for a location name and shows its full active context (self + enclosing + overlapping). A `query` event is logged with the context result.

## Phase 6 - 2026-04-02

### Decision: Use a closed enum for concept_kind

- Rationale: A closed set of valid kinds (primitive, composite, scene_hypothesis, named) provides immediate validation and prevents drift. New kinds can be added to the frozen set in models.py when needed.
- Alternatives considered: Open string with no validation, extensible registry
- Consequences: `_ensure_concept_node()` raises `ValueError` for unknown kinds. CLI rejects invalid kinds with a retry prompt listing valid options.

### Decision: Enforce relation-kind validation at the storage layer

- Rationale: Not all relation kinds make sense between all node types (e.g., `contains` only between locations, `supports` only between concepts). Validating at `_store_graph_edge()` prevents invalid graph topology from ever being persisted.
- Alternatives considered: Validating only at the CLI layer, deferring validation to later phases
- Consequences: `validate_relation()` checks each edge's `relation_kind` against `VALID_RELATION_RULES` before storage. Invalid combinations raise `ValueError`.

### Decision: Make concept creation idempotent

- Rationale: The `_ensure_concept_node()` pattern already returns existing nodes by name. Making `create_concept()` idempotent avoids duplicate nodes if the user accidentally creates the same concept twice.
- Alternatives considered: Raising an error on duplicate creation, offering an update mechanism
- Consequences: Re-creating an existing concept returns the original node without modifying its kind. The session displays "concept exists" instead of an error.

## Phase 7 - 2026-04-02

### Decision: Document exact-fingerprint sensing as a temporary Phase 7 preview

- Rationale: The current `sense /path/to/file` behavior uses SHA-256 file identity, which is useful for iterative progress but is not the target recognition model. Marking it explicitly as temporary prevents it from being treated as a permanent API.
- Alternatives considered: Removing the sensor feature until content-based perception is ready, leaving it undocumented
- Consequences: `SensorObservation` and `SensorBinding` carry docstrings noting Phase 8 replacement. The session banner notes the temporary nature. Regression tests lock the current behavior so Phase 8 can verify a clean transition.

## Phase 8 - 2026-04-02

### Decision: Define ObservationBundle as a frozen dataclass with required field validation

- Rationale: The Perception Architecture Contract specifies 13 fields. Using a frozen dataclass with `__post_init__` validation ensures bundles are immutable and always valid at construction time. Empty required fields (`bundle_id`, `timestamp`, `adapter_id`, `modality`) raise `ValueError` immediately.
- Alternatives considered: Dict-based bundles with ad-hoc validation, TypedDict, Pydantic model
- Consequences: Every sensor adapter must produce a valid `ObservationBundle`. Invalid bundles fail loudly at creation rather than silently at consumption.

### Decision: Use an abstract base class for SensorAdapter

- Rationale: A clear `SensorAdapter` ABC with `adapter_id`, `modality`, and `observe()` as abstract members enforces the adapter contract at the type level. Future adapters (audio, IMU, depth) can be validated against the same interface.
- Alternatives considered: Protocol-based structural typing, free function adapters, duck typing
- Consequences: `ImageAdapter` extends `SensorAdapter`. Type checkers and `isinstance` can verify adapter compliance. New adapters must implement all three abstract members.

### Decision: Preserve SHA-256 fingerprint flow inside ImageAdapter for backward compatibility

- Rationale: Phase 7 sensor bindings use SHA-256 fingerprints as keys. The `ImageAdapter` wraps the existing `SensorObservation.from_path()` flow and stores the resolved path in `raw_refs` and `sensor_origin`. Recognition still relies on fingerprint lookup for now, but all session code receives the bundle interface.
- Alternatives considered: Dropping fingerprint-based recognition immediately, adding perceptual hashing in Phase 8
- Consequences: Existing sensor bindings continue to work. The fingerprint is derivable from `bundle.raw_refs[0]` via `ImageAdapter.sensor_observation_from_bundle()`. Phase 9 introduces content-based features without breaking the current flow.

### Decision: Bump schema to v7 with observation_bundles collection

- Rationale: Persisting bundles alongside sensor bindings supports audit, replay, and later attention scoring. The v6→v7 migration adds an empty `observation_bundles` dict without altering existing data.
- Alternatives considered: Deferring bundle persistence to a later phase, storing bundles only in event logs
- Consequences: Every `bind_sensor_bundle()` call stores the bundle as well as the binding. Bundles are retrievable by `bundle_id` for inspection and replay.

### Decision: Keep adapter selection static (ImageAdapter only)

- Rationale: Only one sensor modality (image files) exists. Dynamic adapter registries, plugin discovery, or runtime selection add complexity without current value. A single `self._image_adapter` attribute in `SessionController` is sufficient.
- Alternatives considered: Adapter registry keyed by modality, auto-detection from file extension, user-selectable adapter
- Consequences: Adding a second adapter in a later phase requires minimal wiring — create the adapter instance and add a selection branch in the sensor handler.
