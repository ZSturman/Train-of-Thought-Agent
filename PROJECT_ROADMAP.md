# Project Roadmap

This file is the master planning layer for the project. It is the authoritative long-range roadmap unless superseded by a documented replan.

## End-State Vision

A continuously learning, inspectable synthetic memory-and-attention engine that anchors early interpretation in location, learns from observation and correction instead of pretrained world knowledge, stores overlapping traces rather than clean named files of memory, and allocates limited top-level processing through partial match, background activation, competition, thresholding, replay, and reconsolidation. Body-relative robot sensing remains one important input domain, but it is no longer the sole definition of the product's final form.

Cross-phase grounding rule: the LLM may help communicate, parse, normalize, and structure user input, but it is never the source of truth. Persisted memory must come only from explicit user input or direct sensor input with explicit provenance.

## Perception Architecture Contract

All future sensing work normalizes raw sensor output into the same transformed input shape before it reaches learning or memory.

- `ObservationBundle` fields:
  - `bundle_id`
  - `timestamp`
  - `adapter_id`
  - `modality`
  - `reference_frame`
  - `pose_estimate`
  - `motion_estimate`
  - `sensor_origin`
  - `regions`
  - `primitive_features`
  - `concept_candidates`
  - `raw_refs`
  - `provenance`
- `regions` are explicit region, patch, or segment descriptors with geometry and salience so "what mattered" is stored instead of guessed from the whole frame later.
- `primitive_features` are modality-neutral percepts such as `blue streak across top`, `green streak across bottom`, `horizontal motion left-to-right`, or `high-frequency burst`.
- `concept_candidates` are graph-linked interpretations supported by one or more primitive features and regions.
- `raw_refs` keep references to the underlying files or live sensor samples without making raw-file identity the final recognition mechanism.
- All sensor adapters must emit this bundle shape, whether the source is image, audio, IMU, wheel odometry, depth, position, or another sensor.

## Cognitive Substrate Contract

The perception stack remains the external cue substrate. Later phases add one repeated internal unit rather than proliferating specialized memory object types.

- `ExperienceFrame` is the current step-level state that wraps one `ObservationBundle` plus active goals, mode, load, recent winners, and prior residue.
- `MemoryUnit` is the generic retained trace shape. It carries `content`, `context`, `priority_signals`, `dynamics`, `links`, and `example_refs`.
- `ActivationState` tracks whether a stored trace is latent, background-active, candidate, active, or persistent.
- `AttentionScore` captures cue match, goal relevance, priority weight, associative support, inhibition, and noise before thresholding.
- `WorkspaceState` represents the small active set that is globally available to top-level system functions.
- `ReplayWindow` represents deferred or low-load re-evaluation windows used for resurfacing, consolidation, and repair.
- `LocationModel` and `LabelNode` remain the bootstrap path in early phases and are cross-linked into later `MemoryUnit` views rather than replaced in one migration.
- "Emotion-like" behavior is always operationalized as `priority_signals` such as mission relevance, risk, uncertainty, anomaly pressure, unresolvedness, recency residue, expected utility, and operator or self relevance.
- The first real runtime schema expansion for this cognitive substrate is intentionally deferred until Phase 13.

## Concept Composition Example

The roadmap uses this worked example as a reference for how cue composition should evolve before it is folded into the broader memory engine:

- Primitive percept: `blue streak across top`
- Primitive percept: `green streak across bottom`
- Named concepts supported by those percepts: `sky`, `grass`, `field`
- Composite cue bundle: `blue streak across top + green streak across bottom`
- Scene hypothesis labels supported by the bundle: `park`, `yard`

The concept graph must be able to save the primitive percepts, the supporting named concepts, the composite cue bundle, and multiple scene labels without forcing one final label too early.

## Phase 1 - Persistent Grayscale Location Bootstrap

- Phase number: 1
- Title: Persistent Grayscale Location Bootstrap
- Purpose: Build a minimal interactive agent with exact-match persistent memory, correction, and append-only logging.
- Prerequisites: None
- In-scope: Exact normalized grayscale lookup, human feedback, persistent storage, append-only event logging, regression tests, validation harness
- Out-of-scope: Noise tolerance, entities, relations, episodes, actions, affordances, composite events, real-world sensing
- Success criteria: The agent learns a grayscale-to-location association, recalls it across restarts, accepts correction, and logs all relevant events and memory mutations
- Risks: Float normalization mistakes, duplicate labels across distinct observations, malformed runtime state
- Likely next phases: 2
- Testing:
  - Run automated tests: `python3 -m pytest tests/ -v` - Phase 1 tests cover exact-match lookup, persistence, correction, and event logging
  - Manual smoke test: (1) Start agent with `python3 -m location_agent.cli`, (2) Enter a value like `0.33` and label it `office`, (3) Enter `0.33` again and verify it guesses `office` with 100% confidence, (4) Confirm with `yes`, (5) Type `quit` then restart the agent and enter `0.33` - it should still remember `office`
  - What to verify: Observations persist in `runtime/location_memory.json` across restarts; all events appear in `runtime/agent_events.jsonl`; correcting a wrong guess updates the stored label; invalid inputs are rejected gracefully

## Phase 2 - Noisy Scalar Matching and Confidence Calibration

- Phase number: 2
- Title: Noisy Scalar Matching and Confidence Calibration
- Purpose: Support small grayscale variation while controlling false positives.
- Prerequisites: Phase 1 completed and validated
- In-scope: Distance-based matching, confidence thresholds, false-positive guards, calibration tests
- Out-of-scope: Multi-observation location models, first-class labels, entities
- Success criteria: Slightly noisy observations can still match the correct location, while unfamiliar values fall below threshold and trigger clarification
- Risks: Overconfident wrong guesses, brittle thresholds
- Likely next phases: 3
- Testing:
  - Run automated tests: `python3 -m pytest tests/ -v` - Phase 2 tests add confidence scoring, distance-based matching, near-collision guards, and reinforced confidence
  - Manual smoke test: (1) Start agent, learn `0.25 -> kitchen`, (2) Enter `0.253` - agent should guess `kitchen` with reduced confidence, (3) Enter `0.31` - should be below threshold and trigger the uncertain-guess or unknown path
  - What to verify: Slightly noisy values within tolerance still match correctly; values beyond tolerance produce weak or zero confidence; the near-collision guard warns before learning a close conflicting value

## Phase 3 - Multi-Observation Location Models

- Phase number: 3
- Title: Multi-Observation Location Models
- Purpose: Merge repeated nearby observations into a single learned location model.
- Prerequisites: Phase 2 completed and validated
- In-scope: Prototype updates, observation aggregation, simple outlier handling, model inspection
- Out-of-scope: First-class labels, relation graphs, generic memory traces
- Success criteria: Repeated observations refine one location model rather than producing uncontrolled duplicates
- Risks: Bad merges, hard-to-explain prototypes
- Likely next phases: 4
- Testing:
  - Run automated tests: `python3 -m pytest tests/ -v` - expects model math, merge, outlier detection, inspect command, schema migration, session behavior, and stress tests
  - Manual smoke test: (1) Start agent, learn `0.25 -> kitchen`, (2) Enter `0.253` and confirm - prototype should shift, (3) Type `inspect` to see the model with updated prototype, spread, and observation count
  - What to verify: Confirming noisy matches merges observations into the model; `inspect` shows prototype, spread, observation count, and guess statistics; schema v2 memory is auto-migrated to v3

## Phase 4 - First-Class Labels

- Phase number: 4
- Title: First-Class Labels
- Purpose: Promote labels into explicit nodes and let reused labels reinforce and widen the same learned location instead of producing naming errors.
- Prerequisites: Phase 3 completed and validated
- In-scope: Label nodes, label-location edges, rename history, alias handling, label reuse reinforcement, span-aware scalar matching across confirmed observations, provenance-ready label and location snapshots
- Out-of-scope: Shared labels across distinct locations, full multi-label ambiguity resolution, generic memory units
- Success criteria: Labels exist independently from single observations, reusing a location label refines the same learned location rather than forcing a new name, and values inside a confirmed location span default to that location unless conflicting evidence appears
- Risks: Migration bugs, identity mismatches between labels and locations, accidental over-merging when a reused label should have been clarified
- Likely next phases: 5, 7
- Phase media: Committed still-image PNG fixtures under `media/core_images/phase04_*` plus the catalog entries in `media/catalog.json`
- Validation scenario: `phase_04_sensor_preview` for direct learn -> recognize -> unrelated-image prompting, with `phase_04_core_scene_gallery` reserving the remaining starter fixtures
- Next sensing bridge: Reuse the same committed image fixtures while introducing parent-context media in Phase 5 without changing the `sense /absolute/path/to/file` entrypoint
- Testing:
  - Run automated tests: `python3 -m pytest tests/ -v` - should include tests for label node creation, label-location edges, rename operations, alias resolution, existing-label reinforcement, and span-aware recognition
  - Manual smoke test: (1) Learn `0.10 -> Point one`, (2) Reuse `Point one` for `0.30` and confirm the outlier merge, (3) Enter `0.28`, (4) Verify the agent now guesses `Point one` by default, (5) Rename or alias the label and confirm the location identity is preserved
  - What to verify: Labels exist as independent nodes; renaming a label updates references; alias handling resolves correctly; reused labels merge into the same location model; schema migration from v3/v4 preserves existing data

## Phase 5 - Nested Location Context

- Phase number: 5
- Title: Nested Location Context
- Purpose: Introduce learned containment and overlap so multiple location contexts can be valid at once.
- Prerequisites: Phase 4 completed and validated
- In-scope: Location containment edges, overlap edges, active-context derivation, context inspection, tests for parent context staying active while children change
- Out-of-scope: Perceptual composition, content-based matching, live sensor calibration
- Success criteria: The agent can keep a larger context such as `house` active while moving between `bedroom` and `living room`
- Risks: Inconsistent parent-child relations, accidental ontology lock-in, confusing overlap vs containment
- Likely next phases: 6, 23
- Phase media: Add a committed containment pack with `house`, `bedroom`, and `living room` scenes that can be taught as co-active context
- Validation scenario: `phase_05_nested_context_walk`
- Next sensing bridge: Carry the same scene through alternate contextual variants so Phase 6 can formalize typed scaffold nodes without losing the location-first footing
- Testing:
  - Run automated tests: `python3 -m pytest tests/ -v` - should include tests for containment links, overlap links, and active-context derivation
  - Manual smoke test: (1) Learn locations for `house`, `bedroom`, and `living room`, (2) Teach `house contains bedroom` and `house contains living room`, (3) Move from bedroom to living room, (4) Verify the child context changes while `house` remains active
  - What to verify: Containment edges are stored explicitly; active context can contain more than one location node; sibling transitions preserve the larger enclosing location

## Phase 6 - Structured Graph and Concept Scaffold

- Phase number: 6
- Title: Structured Graph and Concept Scaffold
- Purpose: Formalize typed graph storage as scaffolding for a later single-unit memory substrate rather than as a permanent many-type ontology.
- Prerequisites: Phase 5 completed and validated
- In-scope: Typed `ConceptNode` contract, expanded `GraphEdge` relation kinds, provenance on nodes and edges, inspection tooling, storage rules for concept aliases and supporting observation references
- Out-of-scope: Region attention, content-based matching, full `MemoryUnit` persistence
- Success criteria: The roadmap and future implementation have a stable bridge from location-first learning into cue composition and later generic memory traces
- Risks: Premature abstraction, bloated graph shape, unclear concept semantics
- Likely next phases: 7, 10
- Phase media: Add same-place context variants and concept-composition prompts that can later map onto primitive and composite cue bundles
- Validation scenario: `phase_06_context_concepts`
- Next sensing bridge: Preserve the current exact-file path learning while preparing for modality-neutral transformed bundles and later `ExperienceFrame` capture
- Testing:
  - Run automated tests: `python3 -m pytest tests/ -v` - should include tests for concept-node creation, typed relation validation, and provenance validation
  - Manual smoke test: (1) Teach a location such as `bedroom`, (2) Attach or inspect typed concepts, (3) Verify concepts, labels, and future cue bundles remain separate graph concerns
  - What to verify: Concepts are documented as typed graph nodes; relation kinds are explicit and inspectable; persisted records still allow only `user` or `sensor` provenance

## Phase 7 - Exact-Fingerprint Sensor Preview

- Phase number: 7
- Title: Exact-Fingerprint Sensor Preview
- Purpose: Keep the current `sense /path/to/file` behavior as a temporary baseline before content-based perception replaces file identity.
- Prerequisites: Phase 6 completed and validated
- In-scope: `sense /path/to/file` flow, direct file fingerprinting, sensor bindings to locations, user confirmation or clarification, sensor event logging
- Out-of-scope: Content-based visual inference, region salience learning, modality fusion, live sensor ingest
- Success criteria: The exact-file preview remains available and clearly documented as temporary rather than the final recognition model
- Risks: Confusing temporary file identity with the intended long-term perception system
- Likely next phases: 8, 11
- Phase media: Formalize the committed image fixtures as an exact-fingerprint preview corpus and add unknown-image prompting cases for regression
- Validation scenario: `phase_07_sensor_preview_regression`
- Next sensing bridge: Replace file-identity assumptions with modality-neutral `ObservationBundle` normalization in Phase 8
- Testing:
  - Run automated tests: `python3 -m pytest tests/ -v` - should include tests for sensor binding, repeated recognition, and provenance-only evidence
  - Manual smoke test: (1) Run `sense /path/to/media`, (2) If unknown, label it, (3) Run the same command again, (4) Verify the location is recognized from the stored file fingerprint, (5) Confirm the docs mark this as a temporary preview
  - What to verify: Sensor bindings rely on direct file fingerprints only in this phase; unknown inputs trigger a user question instead of invention; recognized inputs reuse prior learning

## Phase 8 - Modality-Neutral Observation Bundle

- Phase number: 8
- Title: Modality-Neutral Observation Bundle
- Purpose: Define and adopt one transformed observation interface that every future sensor module must emit.
- Prerequisites: Phase 7 completed and validated
- In-scope: `ObservationBundle` schema, adapter contract, reference-frame placeholders, provenance slots, raw-reference policy, inspection and validation hooks
- Out-of-scope: Region salience learning, generic memory writing, live robot calibration
- Success criteria: Images, audio, motion, and later sensors are all described as the same bundle type before entering learning and memory
- Risks: Overdesigning the contract, conflating raw sensor data with normalized features
- Likely next phases: 9, 11
- Phase media: Add bundle-ready fixtures with placeholder annotations for bundle ids, timestamps, adapter ids, and raw references
- Validation scenario: `phase_08_observation_bundle_contract`
- Next sensing bridge: Populate bundles with explicit regions and primitive features in Phase 9 while keeping the input shape stable enough for later `ExperienceFrame` wrapping
- Testing:
  - Run automated tests: `python3 -m pytest tests/ -v` - should include tests for bundle field validation and adapter normalization invariants
  - Manual smoke test: (1) Feed the same scene through two mock adapters, (2) Verify both produce the same bundle shape, (3) Inspect that the learning interface consumes only the bundle
  - What to verify: `ObservationBundle` fields are explicit and stable; every sensor path is described as adapter -> bundle -> learning; provenance and raw references survive normalization without becoming the recognition key

## Phase 9 - Primitive Percept Features and Region Attention

- Phase number: 9
- Title: Primitive Percept Features and Region Attention
- Purpose: Learn which regions and low-level percepts matter so the agent can remember parts of an observation rather than only the whole.
- Prerequisites: Phase 8 completed and validated
- In-scope: Region descriptors, geometry, salience, primitive percept feature storage, links from features to supporting regions, attention-aware inspection
- Out-of-scope: Composite scene concepts as durable memories, full trace competition
- Success criteria: The agent can save percepts like `blue streak across top` and `green streak across bottom` with explicit region support
- Risks: Too many low-value features, unstable salience heuristics, unclear region vocabulary
- Likely next phases: 10, 15
- Phase media: Add annotated region fixtures and salience scenarios that highlight which patches or segments should drive interpretation
- Validation scenario: `phase_09_region_attention_primitives`
- Next sensing bridge: Use the saved primitive features as the building blocks for compositional cue bundles in Phase 10
- Testing:
  - Run automated tests: `python3 -m pytest tests/ -v` - should include tests for region geometry validation, salience persistence, and feature-to-region linkage
  - Manual smoke test: (1) Load a scene with annotated top and bottom regions, (2) Save primitive features for those regions, (3) Inspect the stored regions and features, (4) Verify the agent can point back to what part of the observation mattered
  - What to verify: Regions are explicit stored objects; salience is inspectable; primitive features are not just free text on the whole observation; supporting regions are traceable

## Phase 10 - Cue Composition and Hypothesis Support

- Phase number: 10
- Title: Cue Composition and Hypothesis Support
- Purpose: Compose primitive cues into higher-level bundles that can support multiple interpretations without collapsing too early into one final scene truth.
- Prerequisites: Phase 9 completed and validated
- In-scope: Primitive vs composite cue kinds, composition edges, supporting observation references, multiple supported hypotheses, inspection of part-whole cue bundles
- Out-of-scope: Generic memory writing, delayed resurfacing, full entity inference
- Success criteria: The graph can save primitive features, named concepts, composite cue bundles, and multiple supported scene hypotheses from the same evidence
- Risks: Composition rules becoming opaque, duplicate cue bundles, premature overcommitment
- Likely next phases: 11, 15
- Phase media: Add concept-composition scenarios centered on the worked example of top blue + bottom green regions producing `sky`, `grass` or `field`, and the scene hypotheses `park` and `yard`
- Validation scenario: `phase_10_cue_composition_hypotheses`
- Next sensing bridge: Wrap composed cues inside `ExperienceFrame` capture in Phase 11 instead of treating them as final standalone memories
- Testing:
  - Run automated tests: `python3 -m pytest tests/ -v` - should include tests for primitive/composite cue kinds, composition edges, and multi-hypothesis support
  - Manual smoke test: (1) Store `blue streak across top`, (2) Store `green streak across bottom`, (3) Link them to `sky` and `grass` or `field`, (4) Create the composite cue bundle, (5) Verify it can support both `park` and `yard` without forcing one winner
  - What to verify: Primitive and composite cue bundles are distinct; composition edges are explicit; one composite can support multiple hypotheses; the worked example is inspectable end to end

## Phase 11 - Experience Frame Capture

- Phase number: 11
- Title: Experience Frame Capture
- Purpose: Wrap each current moment in an `ExperienceFrame` that combines one `ObservationBundle` with goals, mode, load, recent winners, and prior residue.
- Prerequisites: Phase 8 and Phase 10 completed and validated
- In-scope: `ExperienceFrame` contract, goal and mode slots, load indicators, residue tracking, frame inspection, frame-level provenance rules
- Out-of-scope: Persistent `MemoryUnit` creation, attention competition, replay windows
- Success criteria: Every incoming moment can be described as a bounded frame rather than only as a raw bundle or label guess
- Risks: Overstuffed frame schema, mixing observation and interpretation too early
- Likely next phases: 12, 13
- Phase media: Add bundle-plus-context traces that pair one scene with active goal, mode, and residue annotations
- Validation scenario: `phase_11_experience_frame_capture`
- Next sensing bridge: Use the frame sequence to decide where event boundaries belong in Phase 12
- Testing:
  - Run automated tests: `python3 -m pytest tests/ -v` - should include tests for `ExperienceFrame` validation, context slots, and residue capture
  - Manual smoke test: (1) Feed one observation bundle under two different goal modes, (2) Inspect the resulting frames, (3) Verify the bundle stays constant while frame context changes
  - What to verify: Frames preserve bundle provenance; goals and mode are explicit; residue from prior active content is inspectable

## Phase 12 - Event Chunk Boundaries

- Phase number: 12
- Title: Event Chunk Boundaries
- Purpose: Segment streams into meaningful chunks when topic, location, goal, action, social context, or priority shifts enough.
- Prerequisites: Phase 11 completed and validated
- In-scope: Chunk boundary rules, frame-to-chunk aggregation, boundary reasons, chunk inspection, tests for location and goal shifts
- Out-of-scope: Persistent generic memory writing, activation scoring, replay
- Success criteria: Experience is stored as bounded segments rather than one continuous smear
- Risks: Brittle boundary thresholds, over-segmentation, under-segmentation
- Likely next phases: 13, 18
- Phase media: Add short ordered frame traces with clear topic, location, and goal shifts
- Validation scenario: `phase_12_event_chunk_boundaries`
- Next sensing bridge: Use chunked traces as the write candidates in Phase 13
- Testing:
  - Run automated tests: `python3 -m pytest tests/ -v` - should include tests for chunk start and stop rules, shift detection, and stable chunk summaries
  - Manual smoke test: (1) Replay a short sequence with one location shift and one goal shift, (2) Inspect the chunk boundaries, (3) Verify the system creates separate candidates where the shifts matter
  - What to verify: Boundaries are explicit and explainable; chunks retain links to source frames; not every minor frame variation creates a new chunk

## Phase 13 - Memory Write Decisions

- Phase number: 13
- Title: Memory Write Decisions
- Purpose: Introduce the first persisted `MemoryUnit` path and decide whether each chunk creates a new trace, strengthens an old one, links to a prior trace, merges into a repeated pattern, or stays as a weak trace.
- Prerequisites: Phase 12 completed and validated
- In-scope: `MemoryUnit` schema, write-strength policy, create or strengthen decisions, weak-trace storage, mixed storage with `LocationModel` and `LabelNode`, migration scaffolding
- Out-of-scope: Full attention competition, delayed resurfacing, long-horizon replay
- Success criteria: The system writes memory in proportion to significance, distinctiveness, repetition, and priority rather than snapshotting everything equally
- Risks: Schema complexity, bad merges, write policies that are hard to explain
- Likely next phases: 14, 15
- Phase media: Add chunk sets with repeated, novel, low-salience, and high-priority cases so write strength can vary
- Validation scenario: `phase_13_memory_write_decisions`
- Next sensing bridge: Use the same generic `MemoryUnit` type for both distinct instances and repeated-pattern summaries in Phase 14
- Testing:
  - Run automated tests: `python3 -m pytest tests/ -v` - should include tests for create vs strengthen vs link vs weak-trace decisions and mixed-storage migration coverage
  - Manual smoke test: (1) Feed one novel chunk, one repeated chunk, and one weak low-value chunk, (2) Inspect the resulting memory mutations, (3) Verify they do not all write with the same strength
  - What to verify: `MemoryUnit` persistence coexists with the early location store; write decisions are inspectable; mixed storage preserves provenance and inspectability

## Phase 14 - Instance and Aggregate Traces

- Phase number: 14
- Title: Instance and Aggregate Traces
- Purpose: Support both distinct instance memories and compressed repeated-pattern memories with the same `MemoryUnit` substrate.
- Prerequisites: Phase 13 completed and validated
- In-scope: Instance trace markers, aggregate trace markers, exemplar links, repeated-pattern summaries, precision vs stability controls
- Out-of-scope: Attention competition, policy-based inhibition, reconsolidation
- Success criteria: The system can represent one occurrence and the broader "sense of many times" without introducing separate memory classes
- Risks: Overcompression, loss of useful detail, confusing summary traces with specific episodes
- Likely next phases: 15, 22
- Phase media: Add repeated but slightly varying chunk families with one high-impact outlier that should stay distinct
- Validation scenario: `phase_14_instance_aggregate_traces`
- Next sensing bridge: Feed both instance and aggregate traces into partial-match reactivation in Phase 15
- Testing:
  - Run automated tests: `python3 -m pytest tests/ -v` - should include tests for distinct instance retention, repeated-pattern compression, and exemplar back-links
  - Manual smoke test: (1) Replay a recurring situation several times, (2) Add one unusual consequential occurrence, (3) Inspect the stored traces, (4) Verify the recurring pattern broadens while the outlier stays distinct
  - What to verify: Aggregate traces become broader and more stable; exact instances can still be retrieved; exemplars remain linked for inspection

## Phase 15 - Partial Match Reactivation

- Phase number: 15
- Title: Partial Match Reactivation
- Purpose: Let current cues partially activate many stored traces at once instead of performing exact lookup only.
- Prerequisites: Phases 10, 13, and 14 completed and validated
- In-scope: Partial cue overlap, contextual similarity, associative spread, background activation, candidate inspection
- Out-of-scope: Final attention scoring, dynamic thresholds, replay windows
- Success criteria: Several related traces can become weakly active from one current cue, including broad patterns and specific instances
- Risks: Candidate explosion, opaque similarity behavior, overactivation of low-value traces
- Likely next phases: 16, 19
- Phase media: Add cue families where one stimulus should weakly activate several related traces rather than only one exact match
- Validation scenario: `phase_15_partial_match_reactivation`
- Next sensing bridge: Score the reactivated traces against each other in Phase 16
- Testing:
  - Run automated tests: `python3 -m pytest tests/ -v` - should include tests for partial overlap, contextual match, associative support, and background-active candidate sets
  - Manual smoke test: (1) Present one cue tied to a specific event, a broader repeated pattern, and a linked person or mood trace, (2) Inspect the activated set, (3) Verify more than one trace becomes relevant
  - What to verify: Exact lookup is no longer required; background activation is inspectable; associative support can make a weak trace relevant

## Phase 16 - Attention Competition

- Phase number: 16
- Title: Attention Competition
- Purpose: Score partially active traces so only a few rise toward top-level processing.
- Prerequisites: Phase 15 completed and validated
- In-scope: `AttentionScore`, cue match, goal relevance, priority weight, novelty, unresolvedness, associative support, inhibition term, conflict cost, irrelevance penalty, small stochastic noise
- Out-of-scope: Dynamic thresholds, delayed replay, reconsolidation
- Success criteria: Multiple candidates can compete, and the system can explain why some rise while others stay in the background
- Risks: Score inflation, overfitting to hand-tuned weights, hard-to-explain competition outcomes
- Likely next phases: 17, 18
- Phase media: Add competing-cue traces where different goals or priority signals should change the winner
- Validation scenario: `phase_16_attention_competition`
- Next sensing bridge: Gate the scored candidates through dynamic thresholds in Phase 17
- Testing:
  - Run automated tests: `python3 -m pytest tests/ -v` - should include tests for score composition, competing candidates, inhibition penalties, and tie-breaking noise bounds
  - Manual smoke test: (1) Activate several related traces at once, (2) Change the active goal or risk mode, (3) Re-score, (4) Verify the winning candidate changes for explainable reasons
  - What to verify: Cue match alone does not decide everything; goal relevance and operational priority matter; attention scores remain inspectable

## Phase 17 - Dynamic Workspace Thresholds

- Phase number: 17
- Title: Dynamic Workspace Thresholds
- Purpose: Add activation, candidacy, conscious-access, and persistence thresholds that shift with mode and load.
- Prerequisites: Phase 16 completed and validated
- In-scope: Threshold layers, mode-sensitive gating, load-sensitive gating, risk-sensitive gating, persistence rules, threshold inspection
- Out-of-scope: Delayed resurfacing, replay windows, reconsolidation
- Success criteria: The same scored trace can remain latent, become a candidate, or enter workspace depending on the current operating state
- Risks: Thresholds that are too rigid, invisible gating rules, mode explosion
- Likely next phases: 18, 19
- Phase media: Add the same activation set under relaxed, focused, and high-load modes so thresholds visibly shift
- Validation scenario: `phase_17_dynamic_workspace_thresholds`
- Next sensing bridge: Let the winning workspace contents become part of the next cue state in Phase 18
- Testing:
  - Run automated tests: `python3 -m pytest tests/ -v` - should include tests for threshold transitions, mode-dependent threshold movement, and persistence gating
  - Manual smoke test: (1) Re-score one candidate set in relaxed, focused, and high-load modes, (2) Inspect which traces remain latent or active in each mode, (3) Verify thresholds are state-sensitive
  - What to verify: There is more than one threshold; thresholds are dynamic; persistence is separate from initial access

## Phase 18 - Thought Chain Residue

- Phase number: 18
- Title: Thought Chain Residue
- Purpose: Let winning traces feed the next cue state so multi-step thought chains can form.
- Prerequisites: Phase 17 completed and validated
- In-scope: Residue from recent winners, next-cue biasing, neighbor support from active traces, chain inspection, unresolved-loop carryover
- Out-of-scope: Delayed resurfacing, replay windows, reconsolidation
- Success criteria: One selected trace can make another more likely on the next step without requiring an explicit scripted chain
- Risks: Runaway loops, repetitive chains, fragile chaining rules
- Likely next phases: 19, 20
- Phase media: Add short trace sets where one active winner should support a later linked trace or broader theme
- Validation scenario: `phase_18_thought_chain_residue`
- Next sensing bridge: Use residue and subthreshold carryover to explain delayed resurfacing in Phase 19
- Testing:
  - Run automated tests: `python3 -m pytest tests/ -v` - should include tests for residue carryover, next-step cue biasing, and multi-step chain formation
  - Manual smoke test: (1) Trigger one trace, (2) Step the system forward with weak related cues, (3) Inspect the emerging chain, (4) Verify the next thought depends partly on the prior winner
  - What to verify: Winning traces alter what comes next; chains are inspectable as state progression; unresolved loops can keep influence without immediate repetition

## Phase 19 - Delayed Resurfacing

- Phase number: 19
- Title: Delayed Resurfacing
- Purpose: Support subthreshold persistence, replay thresholds, and later resurfacing instead of immediate-only recall.
- Prerequisites: Phases 17 and 18 completed and validated
- In-scope: Subthreshold persistence, replay thresholds, deferred evaluation windows, delayed resurfacing, background-active residue aging
- Out-of-scope: Policy suppression, reconsolidation
- Success criteria: A trace can matter now, stay below awareness, and resurface later when the context or thresholds shift
- Risks: Unclear replay timing, noisy resurfacing, too much hidden state
- Likely next phases: 20, 21
- Phase media: Add delayed-cue traces where the first match is weak but later support or lower load should bring the trace forward
- Validation scenario: `phase_19_delayed_resurfacing`
- Next sensing bridge: Add policy-based filtering so some strong traces can still be blocked in Phase 20
- Testing:
  - Run automated tests: `python3 -m pytest tests/ -v` - should include tests for replay thresholds, delayed resurfacing, and persistence decay
  - Manual smoke test: (1) Present a weak cue, (2) Keep the trace below workspace, (3) Later add supporting context or lower the load, (4) Verify the trace resurfaces
  - What to verify: Subthreshold traces are not discarded immediately; replay windows can reactivate a trace later; delayed resurfacing is explainable without subjective language

## Phase 20 - Policy Inhibition Controls

- Phase number: 20
- Title: Policy Inhibition Controls
- Purpose: Model suppression-like behavior as policy filtering, quarantine, and strong-but-blocked traces.
- Prerequisites: Phases 16, 17, and 19 completed and validated
- In-scope: Inhibition policies, quarantine states, strong-but-blocked traces, stability guards, computation-budget penalties, policy inspection
- Out-of-scope: Reconsolidation, long-horizon audit tooling
- Success criteria: Important traces can still be blocked from workspace when doing so protects the active task, system stability, or policy constraints
- Risks: Overblocking useful traces, hidden policy behavior, brittle quarantine rules
- Likely next phases: 21, 27
- Phase media: Add trace sets where a high-priority candidate should still be blocked because of mode, cost, or policy
- Validation scenario: `phase_20_policy_inhibition_controls`
- Next sensing bridge: Make recall editable after release from policy gating in Phase 21
- Testing:
  - Run automated tests: `python3 -m pytest tests/ -v` - should include tests for policy down-weighting, quarantine release, and strong-but-blocked outcomes
  - Manual smoke test: (1) Activate a strong but disruptive trace during a focused mode, (2) Verify it is blocked, (3) Relax the mode or clear the policy, (4) Verify it can then compete again
  - What to verify: Blocking is not the same as weakness; policy reasons are inspectable; strong traces can remain backgrounded without disappearing

## Phase 21 - Recall Reconsolidation

- Phase number: 21
- Title: Recall Reconsolidation
- Purpose: Make reactivation rewrite future accessibility, links, interpretation, and cue sensitivity instead of acting as a read-only lookup.
- Prerequisites: Phases 19 and 20 completed and validated
- In-scope: Reconsolidation windows, post-recall updates, accessibility changes, link updates, context absorption, interpretation shifts
- Out-of-scope: Large-scale repeated-pattern compression, operator audit tooling
- Success criteria: Recalling a trace changes how it behaves later, including which contexts can cue it and what neighbors it supports
- Risks: Unintended drift, overediting stable traces, unclear reconsolidation scope
- Likely next phases: 22, 28
- Phase media: Add recall-and-update traces where the same prior trace is reactivated under new context and should later behave differently
- Validation scenario: `phase_21_recall_reconsolidation`
- Next sensing bridge: Use repeated recall and repeated exposure to drive broader pattern compression in Phase 22
- Testing:
  - Run automated tests: `python3 -m pytest tests/ -v` - should include tests for reconsolidation windows, accessibility changes, and post-recall link updates
  - Manual smoke test: (1) Reactivate an older trace under new context, (2) Inspect the updated trace, (3) Trigger a later cue, (4) Verify the changed accessibility or interpretation matters
  - What to verify: Recall is not read-only; links and accessibility can change; new context can update old traces without erasing provenance

## Phase 22 - Repetition Compression

- Phase number: 22
- Title: Repetition Compression
- Purpose: Compress repeated experiences into broader, more stable summary traces while preserving exemplar links and important exceptions.
- Prerequisites: Phases 14 and 21 completed and validated
- In-scope: Repetition-based compression, summary trace stability, exemplar retention, exception preservation, broader cueability
- Out-of-scope: Emergent structural views, unusual sensing adaptation
- Success criteria: Repeated experiences collapse into a "sense of many times" rather than only a bag of separate episodes
- Risks: Flattening meaningful variation, losing high-impact exceptions, brittle compression rules
- Likely next phases: 23, 27
- Phase media: Add several recurring trace families with slight variation and one emotionally or operationally high-impact exception
- Validation scenario: `phase_22_repetition_compression`
- Next sensing bridge: Expose higher-level structure as views over these compressed traces in Phase 23
- Testing:
  - Run automated tests: `python3 -m pytest tests/ -v` - should include tests for repetition compression, exemplar back-links, and exception retention
  - Manual smoke test: (1) Replay a recurring family of experiences, (2) Inspect the new summary trace, (3) Verify variable details weaken while recurring tone and structure strengthen
  - What to verify: Summary traces become easier to cue; differing details soften; exemplar instances remain recoverable

## Phase 23 - Emergent Structure Views

- Phase number: 23
- Title: Emergent Structure Views
- Purpose: Express relations, entities, affordances, and spatial transitions as emergent views over `MemoryUnit` graphs instead of as separate permanent memory classes.
- Prerequisites: Phases 15, 20, and 22 completed and validated
- In-scope: Derived structure views, view generation rules, inspectable relation and entity projections, affordance and transition projections, provenance back-links
- Out-of-scope: Non-human sensing adaptation, multimodal live ingest
- Success criteria: Higher-level structure can be inspected and used without abandoning the single-unit memory design principle
- Risks: View inconsistency, accidental reintroduction of many bespoke memory types, opaque derivation logic
- Likely next phases: 24, 25
- Phase media: Add trace families rich enough to derive relations, roles, affordances, and transitions from recurring memory structure
- Validation scenario: `phase_23_emergent_structure_views`
- Next sensing bridge: Stress the same derived-view rules against unusual sensing domains in Phase 24
- Testing:
  - Run automated tests: `python3 -m pytest tests/ -v` - should include tests for relation view generation, entity view generation, and affordance or transition projections from shared traces
  - Manual smoke test: (1) Build a mixed trace set, (2) Inspect the derived views, (3) Verify the system can expose relation or entity structure without storing them as unrelated base memory types
  - What to verify: Derived views stay linked to the same underlying traces; provenance survives projection; the single-unit substrate remains intact

## Phase 24 - Nonhuman Signal Abstraction

- Phase number: 24
- Title: Nonhuman Signal Abstraction
- Purpose: Adapt the same architecture to unusual or non-human sensing channels, sparse evidence, and system-relative regularities.
- Prerequisites: Phases 8, 15, and 23 completed and validated
- In-scope: Unusual-signal examples, sparse-input handling, confidence and uncertainty handling for thin evidence, system-relative feature abstraction
- Out-of-scope: Pose and motion context, synchronized multimodal live ingest
- Success criteria: The architecture can form traces and resurfacing behavior from signals humans would not naturally group or even perceive
- Risks: Human-centric assumptions leaking into abstraction rules, brittle sparse-input behavior
- Likely next phases: 25, 26
- Phase media: Add unusual-sensing fixtures such as synthetic timing distributions, machine-state correlations, or sparse cross-channel signatures that still map into `ObservationBundle`
- Validation scenario: `phase_24_nonhuman_signal_abstraction`
- Next sensing bridge: Reintroduce pose, motion, and sensor origin as context dimensions inside the same trace system in Phase 25
- Testing:
  - Run automated tests: `python3 -m pytest tests/ -v` - should include tests for unusual sensing abstraction, sparse-evidence weighting, and system-relative cueing
  - Manual smoke test: (1) Feed a non-visual or non-human-like cue family, (2) Inspect the resulting traces, (3) Verify abstraction follows recurring system structure rather than human categories
  - What to verify: Non-human signals can still drive trace writing and resurfacing; uncertainty stays explicit; abstraction remains grounded in direct evidence

## Phase 25 - Pose and Motion Context

- Phase number: 25
- Title: Pose and Motion Context
- Purpose: Make pose, motion, and sensor origin part of context and thresholding rather than a separate end-state track.
- Prerequisites: Phases 8, 17, and 24 completed and validated
- In-scope: `reference_frame`, `pose_estimate`, `motion_estimate`, `sensor_origin`, context-sensitive thresholding, motion-aware cue matching, body-relative inspection
- Out-of-scope: Full synchronized multimodal live ingest
- Success criteria: Body-relative context can change which traces reactivate and how strongly they compete without redefining the core memory architecture
- Risks: Frame confusion, drift, overcoupling context to one robot embodiment
- Likely next phases: 26, 27
- Phase media: Add pose-annotated and motion-annotated replay bundles that change reactivation or threshold outcomes
- Validation scenario: `phase_25_pose_motion_context`
- Next sensing bridge: Feed these contextualized traces through synchronized multimodal ingest in Phase 26
- Testing:
  - Run automated tests: `python3 -m pytest tests/ -v` - should include tests for pose and motion field validation, body-relative context scoring, and sensor-origin-aware threshold changes
  - Manual smoke test: (1) Replay one cue family from different orientations or motion states, (2) Inspect the changed activation and threshold outcomes, (3) Verify pose and motion behave as context rather than as a separate subsystem
  - What to verify: Pose and motion are first-class context fields; body-relative context changes accessibility; shared trace-writing rules still apply

## Phase 26 - Multimodal Trace Ingest

- Phase number: 26
- Title: Multimodal Trace Ingest
- Purpose: Feed synchronized multimodal inputs into the same write, activation, and competition engine.
- Prerequisites: Phases 8, 13, and 25 completed and validated
- In-scope: Sensor adapters, synchronized `ObservationBundle` creation, multimodal `ExperienceFrame` capture, multimodal write decisions, shared trace logging
- Out-of-scope: Continuous live monitoring and long-horizon repair workflows
- Success criteria: Vision, audio, timing, position, and motion cues can all enter the same trace-writing and reactivation pipeline without modality-specific memory silos
- Risks: Synchronization bugs, latency, bundle overloading
- Likely next phases: 27
- Phase media: Add synchronized multimodal bundles that pair images with audio, timestamps, position traces, and pose or motion fields under one scenario id
- Validation scenario: `phase_26_multimodal_trace_ingest`
- Next sensing bridge: Convert replay bundles into longer live-like streams with drift and corrections for Phase 27
- Testing:
  - Run automated tests: `python3 -m pytest tests/ -v` - should include tests for sensor adapters, multimodal frame capture, and shared write-path invariants
  - Manual smoke test: (1) Feed simulated multimodal bundles, (2) Verify they enter the same write and activation pipeline, (3) Inspect synchronized trace support across modalities
  - What to verify: Sensor adapters normalize diverse inputs into `ObservationBundle`; synchronized observations are logged atomically; multimodal traces do not bypass the generic memory engine

## Phase 27 - Live Cognitive Monitoring

- Phase number: 27
- Title: Live Cognitive Monitoring
- Purpose: Run continuous background activation, resurfacing, inhibition, and correction loops under live-like load.
- Prerequisites: Phases 19, 20, 22, 25, and 26 completed and validated
- In-scope: Continuous monitoring, background activation under load, delayed resurfacing under stream conditions, live correction loop, drift handling for context and thresholds
- Out-of-scope: Operator audit tooling and repair suites
- Success criteria: The system can sustain ongoing cue intake while maintaining a coherent active set, delayed resurfacing behavior, and correction-driven adjustment over time
- Risks: State drift, runaway background activation, overloaded replay queues
- Likely next phases: 28
- Phase media: Add long-running live-like multimodal replays with drift, noise injection, motion changes, and repeated corrections across contexts
- Validation scenario: `phase_27_live_cognitive_monitoring`
- Next sensing bridge: Retain the same replay corpora as auditable operator cases for Phase 28 tooling and repair workflows
- Testing:
  - Run automated tests: `python3 -m pytest tests/ -v` - should include tests for continuous activation, delayed resurfacing under load, correction loops, and drift handling
  - Manual smoke test: (1) Run continuous monitoring with simulated live multimodal input, (2) Trigger competing cues and delayed resurfacing, (3) Correct a mistaken activation pattern, (4) Verify the system adjusts without losing coherence
  - What to verify: Live-like monitoring preserves background vs active distinctions; delayed resurfacing still works under load; correction loops update future competition and thresholds

## Phase 28 - Operator Audit and Repair

- Phase number: 28
- Title: Operator Audit and Repair
- Purpose: Make the system dependable, inspectable, and repairable over long deployments and iterative corrections.
- Prerequisites: Phase 27 completed and validated
- In-scope: Replay tooling, audit views, drift detection, trace repair workflows, regression suites, explainability for write and activation histories
- Out-of-scope: New sensing modalities
- Success criteria: Operators can inspect how a trace was written, compressed, reactivated, blocked, surfaced, and rewritten, then repair mistakes without discarding the whole memory substrate
- Risks: Operational complexity, incomplete audit coverage, repair actions that damage provenance
- Likely next phases: Iterative refinement only
- Phase media: Add long-horizon replay corpora, annotated drift cases, repair-focused audit bundles, and operator review scenarios
- Validation scenario: `phase_28_operator_audit`
- Next sensing bridge: Iterative refinement only; add new corpora without changing `ObservationBundle` unless a new modality is explicitly in scope
- Testing:
  - Run automated tests: `python3 -m pytest tests/ -v` - should include regression suites, replay validation, drift detection tests, repair workflow tests, and trace-explainability checks
  - Manual smoke test: (1) Run the system for an extended session, (2) Use replay tooling to audit a resurfacing chain and a blocked trace, (3) Trigger a drift condition and verify detection, (4) Use repair workflows to correct the behavior and confirm recovery
  - What to verify: Replay tooling accurately reconstructs past state; audit views are complete and inspectable; repair workflows preserve provenance while restoring correct behavior; the system remains trustworthy over long-horizon operation

---

## Phase Documentation Standard

When a phase becomes active, `CURRENT_PHASE.md` must be updated to include the following sections in addition to the phase specification:

### Required "How to Run This Phase" Section

Every `CURRENT_PHASE.md` must include a **How to Run This Phase** block near the top containing:

1. **Prerequisites** - Python version, any new dependencies, required prior state
2. **Quick Start** - The exact command(s) to run the phase's functionality
3. **Example Session** - A complete copy-pasteable terminal session showing:
   - What the user types
   - What the agent outputs
   - Annotations explaining what is happening at each step
4. **Running Tests** - The exact test command and expected pass count
5. **What to Check After Running** - Which files to inspect and what they should contain
6. **What Success Looks Like** - A numbered list of observable behaviors that confirm the phase works
7. **Phase Media** - Required asset ids or packs, scenario ids, exact file paths or commands, expected outcomes, and whether the inputs are committed fixtures or later live sources
8. **Sensor Contract** - For any sensing phase, the active `ObservationBundle` fields, `ExperienceFrame` assumptions, attention or threshold requirements, and whether the phase still depends on the temporary exact-file preview

This standard ensures that any user encountering the project at any phase can immediately understand what to do, what to expect, and how to verify correctness without needing prior context or external documentation.
