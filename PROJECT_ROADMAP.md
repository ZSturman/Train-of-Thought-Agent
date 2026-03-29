# Project Roadmap

This file is the master planning layer for the project. It is the authoritative long-range roadmap unless superseded by a documented replan.

## End-State Vision

A continuously learning, inspectable agent that anchors interpretation in location, learns from observation and correction instead of pretrained world knowledge, forms labels, entities, relations, episodes, affordances, and composite events online, and ultimately reasons about real-world location change at the granularity of doorway, hallway, room, and building.

Cross-phase grounding rule: the LLM may help communicate, parse, normalize, and structure user input, but it is never the source of truth. Persisted memory must come only from explicit user input or direct sensor input with explicit provenance.

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
  - Run automated tests: `python3 -m pytest tests/ -v` — Phase 1 tests cover exact-match lookup, persistence, correction, and event logging
  - Manual smoke test: (1) Start agent with `python3 -m location_agent.cli`, (2) Enter a value like `0.33` and label it "office", (3) Enter `0.33` again and verify it guesses "office" with 100% confidence, (4) Confirm with `yes`, (5) Type `quit` then restart the agent and enter `0.33` — it should still remember "office"
  - What to verify: Observations persist in `runtime/location_memory.json` across restarts; all events appear in `runtime/agent_events.jsonl`; correcting a wrong guess updates the stored label; invalid inputs (negative numbers, text, values >1.0) are rejected gracefully

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
  - Run automated tests: `python3 -m pytest tests/ -v` — Phase 2 tests add confidence scoring, distance-based matching, near-collision guards, and reinforced confidence
  - Manual smoke test: (1) Start agent, learn `0.25` → "kitchen", (2) Enter `0.253` — agent should guess "kitchen" with reduced confidence (~94%), (3) Enter `0.31` — should be below threshold and trigger the uncertain-guess or unknown path, (4) Enter `0.25` again near an existing model — near-collision guard should warn
  - What to verify: Slightly noisy values within tolerance (0.05) still match correctly; values beyond tolerance produce zero or weak confidence; the near-collision guard warns before learning a value close to an existing one; schema v1 memory files are auto-migrated to v2 on load

## Phase 3 - Multi-Observation Location Models

- Phase number: 3
- Title: Multi-Observation Location Models
- Purpose: Merge repeated nearby observations into a single learned location model.
- Prerequisites: Phase 2 completed and validated
- In-scope: Prototype updates, observation aggregation, simple outlier handling, model inspection
- Out-of-scope: First-class labels, entities, relation graphs
- Success criteria: Repeated observations refine one location model rather than producing uncontrolled duplicates
- Risks: Bad merges, hard-to-explain prototypes
- Likely next phases: 4
- Testing:
  - Run automated tests: `python3 -m pytest tests/ -v` — expects model math, merge, outlier detection, inspect command, schema migration, session behavior, and stress tests
  - Manual smoke test: (1) Start agent, learn `0.25` → "kitchen", (2) Enter `0.253` and confirm — prototype should shift, (3) Type `inspect` to see the model with updated prototype, spread, and observation count, (4) Enter an outlier value far from any model — outlier warning should appear, (5) Type `reset` and confirm — `inspect` should show no models
  - What to verify: Confirming noisy matches merges observations into the model (prototype shifts toward new value); `inspect` shows prototype, spread, observation count, correct/wrong counts; outlier detection warns for values >3× max(spread, tolerance) from prototype; schema v2 memory is auto-migrated to v3; `reset` clears all models

## Phase 4 - First-Class Labels

- Phase number: 4
- Title: First-Class Labels
- Purpose: Promote labels into explicit nodes and let reused labels reinforce and widen the same learned location instead of producing naming errors.
- Prerequisites: Phase 3 completed and validated
- In-scope: Label nodes, label-location edges, rename history, alias handling, label reuse reinforcement, span-aware scalar matching across confirmed observations, provenance-ready label and location snapshots
- Out-of-scope: Shared labels across distinct locations, full multi-label ambiguity resolution, entities
- Success criteria: Labels exist independently from single observations, reusing a location label refines the same learned location rather than forcing a new name, and values inside a confirmed location span default to that location unless conflicting evidence appears
- Risks: Migration bugs, identity mismatches between labels and locations, accidental over-merging when a reused label should have been clarified
- Likely next phases: 5, 12
- Testing:
  - Run automated tests: `python3 -m pytest tests/ -v` — should include tests for label node creation, label-location edges, rename operations, alias resolution, existing-label reinforcement, and span-aware recognition inside a confirmed range
  - Manual smoke test: (1) Learn `0.10` → "Point one", (2) Reuse "Point one" for `0.30` and confirm the outlier merge, (3) Enter `0.28`, (4) Verify the agent now guesses "Point one" by default because it falls inside the confirmed span, (5) Rename or alias the label and confirm the location identity is preserved
  - What to verify: Labels exist as independent nodes rather than plain strings on locations; renaming a label updates all references; alias handling resolves correctly; reused labels merge into the same location model; values inside the learned scalar span are matched against that location by default instead of only against the running prototype; schema migration from v3/v4 preserves existing data

## Phase 5 - Nested Location Context

- Phase number: 5
- Title: Nested Location Context
- Purpose: Introduce learned containment and overlap so multiple location contexts can be valid at once.
- Prerequisites: Phase 4 completed and validated
- In-scope: Location containment edges, overlap edges, active-context derivation, context inspection, tests for parent context staying active while children change
- Out-of-scope: Entities, full ambiguity policy, room/building ontology lock-in
- Success criteria: The agent can keep a larger context such as "house" active while moving between "bedroom" and "living room"
- Risks: Inconsistent parent-child relations, accidental ontology lock-in, confusing overlap vs containment
- Likely next phases: 6, 17
- Testing:
  - Run automated tests: `python3 -m pytest tests/ -v` — should include tests for containment links, overlap links, and active-context derivation
  - Manual smoke test: (1) Learn locations for `house`, `bedroom`, and `living room`, (2) Teach `house contains bedroom` and `house contains living room`, (3) Move from bedroom to living room, (4) Verify the child context changes while `house` remains active
  - What to verify: Containment edges are stored explicitly; active context can contain more than one location node; sibling transitions preserve the larger enclosing location

## Phase 6 - Location Graph and Node Setup

- Phase number: 6
- Title: Location Graph and Node Setup
- Purpose: Formalize location, label, concept, and relationship scaffolding so later disambiguation can refine rather than redesign the memory model.
- Prerequisites: Phase 5 completed and validated
- In-scope: Typed graph edges, concept nodes, location-concept links, provenance on nodes and edges, inspection tooling
- Out-of-scope: Full multi-label reasoning, entities, affordances
- Success criteria: Location labels, concepts, and their relationships exist as first-class graph structures that support later refinement
- Risks: Premature abstraction, bloated graph shape, unclear concept semantics
- Likely next phases: 7, 13
- Testing:
  - Run automated tests: `python3 -m pytest tests/ -v` — should include tests for concept-node creation, location-concept links, and provenance validation
  - Manual smoke test: (1) Teach a location such as `bedroom`, (2) Attach a concept such as `morning`, (3) Inspect the graph, (4) Verify the concept is stored as a node and linked to the location without becoming ground truth by itself
  - What to verify: Labels and concepts are separate node types; graph edges are typed and inspectable; persisted records show provenance only from `user` or `sensor`

## Phase 7 - Simulated Sensor Location Recognition

- Phase number: 7
- Title: Simulated Sensor Location Recognition
- Purpose: Add a CLI-first path harness for image, video, or other files as direct sensor input before real-world multimodal ingestion.
- Prerequisites: Phase 6 completed and validated
- In-scope: `sense /path/to/file` flow, direct file fingerprinting, sensor bindings to locations, user confirmation or clarification, sensor event logging
- Out-of-scope: Real-world live ingestion, multimodal fusion, model-based visual inference
- Success criteria: Given a file path, the system either recognizes the location from prior direct learning or asks the user what location the file represents
- Risks: Exact fingerprint matching may be too brittle, path handling errors, accidentally storing inferred facts instead of direct evidence
- Likely next phases: 8, 19
- Testing:
  - Run automated tests: `python3 -m pytest tests/ -v` — should include tests for sensor binding, repeated recognition, and provenance-only evidence
  - Manual smoke test: (1) Run `sense /path/to/media`, (2) If unknown, label it, (3) Run the same command again, (4) Verify the location is recognized and confirmed from the stored sensor binding
  - What to verify: Sensor bindings rely on direct file fingerprints; unknown inputs trigger a user question instead of invention; recognized inputs reuse prior learning; memory records cite only `user` and `sensor` provenance

## Phase 8 - Minimal Scene Entities

- Phase number: 8
- Title: Minimal Scene Entities
- Purpose: Add simple entity observations inside the simulator without hardcoded world structure.
- Prerequisites: Phases 4, 5, 6, and 7 completed and validated
- In-scope: Entity nodes, observed-at-location links, simple entity logging and tests
- Out-of-scope: Rich relations, affordances, action semantics
- Success criteria: The agent can learn that locations are associated with observed entities from experience
- Risks: Confusing labels with entities, overcomplicating the simulator too early
- Likely next phases: 9
- Testing:
  - Run automated tests: `python3 -m pytest tests/ -v` — should include tests for entity creation, observed-at links, and entity persistence
  - Manual smoke test: (1) Learn a location, (2) Add an entity observation at that location, (3) Inspect to verify the entity-location link exists, (4) Restart and confirm entity associations persist
  - What to verify: Entity nodes are distinct from label nodes and concept nodes; observed-at-location links are correctly stored and retrievable; entity logging captures all mutations; entities persist across sessions

## Phase 9 - Location-Conditioned Entity Inference

- Phase number: 9
- Title: Location-Conditioned Entity Inference
- Purpose: Make interpretation of cues depend on location context.
- Prerequisites: Phase 8 completed and validated
- In-scope: Entity likelihood by location, context-sensitive retrieval, tests for same cue in different places
- Out-of-scope: Full relation graph semantics, temporal episode modeling
- Success criteria: The same sensory cue can lead to different inferred entities depending on location context
- Risks: Brittle priors, leaking assumptions into learned inference
- Likely next phases: 10, 11
- Testing:
  - Run automated tests: `python3 -m pytest tests/ -v` — should include tests for context-sensitive retrieval and same-cue-different-place scenarios
  - Manual smoke test: (1) Set up two locations with the same sensory cue but different entities, (2) Observe the cue in each location context, (3) Verify the agent infers different entities based on location
  - What to verify: The same cue produces different entity inferences depending on location context; entity likelihoods are computed per-location; context-sensitive retrieval does not leak cross-location assumptions

## Phase 10 - Relations Graph

- Phase number: 10
- Title: Relations Graph
- Purpose: Introduce explicit learned relations such as contains, near, connected-to, and co-occurs.
- Prerequisites: Phase 9 completed and validated
- In-scope: Inspectable graph edges, relation queries, relation mutation logging
- Out-of-scope: Episodic sequencing, clarification workflows
- Success criteria: Relation-based retrieval is possible and explainable using learned graph edges
- Risks: Edge explosion, inconsistent relation semantics
- Likely next phases: 11
- Testing:
  - Run automated tests: `python3 -m pytest tests/ -v` — should include tests for relation creation, graph queries, and mutation logging
  - Manual smoke test: (1) Create locations and entities, (2) Establish relations (contains, near, connected-to), (3) Query relations and verify correct edges are returned, (4) Inspect the graph for expected structure
  - What to verify: Relations are stored as inspectable graph edges; relation-based retrieval returns correct results; relation mutations are logged; inconsistent or duplicate relations are handled gracefully

## Phase 11 - Episodic Memory and Temporal Sequences

- Phase number: 11
- Title: Episodic Memory and Temporal Sequences
- Purpose: Store ordered experiences and recall recent sequences.
- Prerequisites: Phase 10 completed and validated
- In-scope: Episode records, temporal ordering, replay support, recency-aware retrieval
- Out-of-scope: Clarification policy, composite event abstraction
- Success criteria: The agent can store and inspect ordered sequences of observations and transitions
- Risks: Storage growth, unclear episode boundaries
- Likely next phases: 12, 16
- Testing:
  - Run automated tests: `python3 -m pytest tests/ -v` — should include tests for episode creation, temporal ordering, replay, and recency-aware retrieval
  - Manual smoke test: (1) Perform a sequence of observations, (2) Replay the episode to verify order is preserved, (3) Test recency-aware retrieval returns recent episodes first
  - What to verify: Ordered sequences of observations are stored correctly; replay produces the same sequence; recency-aware retrieval works; episode boundaries are defined consistently

## Phase 12 - Ambiguity Detection and Clarification

- Phase number: 12
- Title: Ambiguity Detection and Clarification
- Purpose: Detect when current evidence supports multiple plausible interpretations and ask careful clarifying questions instead of silently overcommitting.
- Prerequisites: Phases 4 and 11 completed and validated
- In-scope: Ambiguity state tracking, clarification prompts, unresolved-memory support, overlapping/contextual location-label clarification
- Out-of-scope: Subtype taxonomies, affordances, actions
- Success criteria: The agent asks for clarification instead of silently overcommitting when evidence is ambiguous, including overlapping or contextual location labels
- Risks: Excessive questioning, poor ambiguity thresholds
- Likely next phases: 13
- Testing:
  - Run automated tests: `python3 -m pytest tests/ -v` — should include tests for ambiguity detection, clarification prompts, and unresolved-memory handling
  - Manual smoke test: (1) Create overlapping or conflicting evidence, (2) Verify the agent detects ambiguity and asks clarifying questions instead of committing, (3) Provide clarification and verify it resolves correctly
  - What to verify: Ambiguous evidence triggers clarification prompts; the agent does not silently overcommit when multiple interpretations are plausible; unresolved states are stored and can be revisited; clarification successfully resolves ambiguity

## Phase 13 - Category Refinement and Subtype Learning

- Phase number: 13
- Title: Category Refinement and Subtype Learning
- Purpose: Support broad labels and later subtype distinctions through repeated experience and correction, with concept nodes carrying the refinement structure.
- Prerequisites: Phase 12 completed and validated
- In-scope: Category and subtype links, refinement logic, correction-driven updates, contextual multi-label distinction support
- Out-of-scope: Affordances, actions
- Success criteria: Shared labels can coexist with more precise subtype distinctions when ambiguity is clarified
- Risks: Premature category splitting, unstable refinements
- Likely next phases: 14
- Testing:
  - Run automated tests: `python3 -m pytest tests/ -v` — should include tests for category creation, subtype linking, and correction-driven refinement
  - Manual smoke test: (1) Teach a broad label, (2) Provide corrections that introduce subtype distinctions, (3) Verify both the broad label and subtypes coexist, (4) Inspect category-subtype hierarchy
  - What to verify: Broad labels can coexist with more precise subtype distinctions; correction-driven updates refine categories without losing the parent label; concept/category links are inspectable

## Phase 14 - Affordances

- Phase number: 14
- Title: Affordances
- Purpose: Learn what locations or entities enable without hardcoding symbolic knowledge.
- Prerequisites: Phases 8 and 13 completed and validated
- In-scope: Affordance nodes or edges, affordance evidence, retrieval and inspection
- Out-of-scope: Executable action primitives
- Success criteria: The agent can represent learned affordances grounded in experience
- Risks: Sparse evidence, confusing observed outcomes with possibilities
- Likely next phases: 15
- Testing:
  - Run automated tests: `python3 -m pytest tests/ -v` — should include tests for affordance creation, evidence accumulation, and affordance retrieval
  - Manual smoke test: (1) Teach locations and entities, (2) Associate affordances through experience, (3) Retrieve and inspect affordances, (4) Verify affordances are grounded in evidence not assumptions
  - What to verify: Affordance nodes/edges are created from experience; affordance evidence accumulates correctly; retrieval returns only learned affordances; inspection shows the evidence supporting each affordance

## Phase 15 - Action Primitives in Simulation

- Phase number: 15
- Title: Action Primitives in Simulation
- Purpose: Add a minimal action loop and learn from action outcomes.
- Prerequisites: Phase 14 completed and validated
- In-scope: Small action set, outcome logging, correction-driven outcome updates
- Out-of-scope: Composite event discovery, real-world sensing
- Success criteria: Action outcomes modify learned state through the same online learning principles
- Risks: Credit assignment mistakes, simulator complexity creep
- Likely next phases: 16
- Testing:
  - Run automated tests: `python3 -m pytest tests/ -v` — should include tests for action execution, outcome logging, and correction-driven outcome updates
  - Manual smoke test: (1) Execute an action in the simulator, (2) Observe and log the outcome, (3) Correct an incorrect outcome prediction, (4) Verify the correction updates learned state
  - What to verify: Actions produce logged outcomes; outcomes modify learned state through online learning; corrections update outcome predictions; the action set is minimal and well-defined

## Phase 16 - Composite Event Discovery

- Phase number: 16
- Title: Composite Event Discovery
- Purpose: Let higher-level events emerge from repeated lower-level temporal structure.
- Prerequisites: Phases 11 and 15 completed and validated
- In-scope: Repeated-sequence clustering, composite event records, inspection and validation tools
- Out-of-scope: Spatial hierarchy, real-world deployment
- Success criteria: Stable composite events can be discovered without hardcoded event labels
- Risks: Over-grouping, under-grouping, opaque abstractions
- Likely next phases: 17
- Testing:
  - Run automated tests: `python3 -m pytest tests/ -v` — should include tests for repeated-sequence clustering, composite event creation, and inspection tools
  - Manual smoke test: (1) Produce repeated low-level sequences, (2) Verify composite events emerge from the patterns, (3) Inspect composite events to confirm they are explainable
  - What to verify: Repeated temporal patterns produce composite event records; composite events are discoverable without hardcoded labels; inspection tools show constituent sequences; over-grouping and under-grouping are controlled

## Phase 17 - Spatial Transitions and Doorway-Hallway Reasoning

- Phase number: 17
- Title: Spatial Transitions and Doorway-Hallway Reasoning
- Purpose: Learn transitions, room boundaries, and doorway or hallway distinctions in simulation.
- Prerequisites: Phases 11 and 16 completed and validated
- In-scope: Transition detection, boundary-state modeling, hallway-vs-room reasoning
- Out-of-scope: Building hierarchy, multimodal sensing
- Success criteria: The agent detects room changes, doorway traversal, and transition structure
- Risks: Noisy boundary states, unclear transition segmentation
- Likely next phases: 18
- Testing:
  - Run automated tests: `python3 -m pytest tests/ -v` — should include tests for transition detection, boundary-state modeling, and hallway-vs-room classification
  - Manual smoke test: (1) Simulate moving through a sequence of rooms and hallways, (2) Verify the agent detects transitions at boundaries, (3) Inspect transition records for correct room and doorway classifications
  - What to verify: Room changes are detected correctly; doorway traversal is identified; transition structure is inspectable; noisy boundary states do not produce false transitions

## Phase 18 - Room and Building Hierarchy

- Phase number: 18
- Title: Room and Building Hierarchy
- Purpose: Extend the earlier location-context scaffolding into richer nested reasoning for buildings, floors, rooms, and hallways.
- Prerequisites: Phase 17 completed and validated
- In-scope: Hierarchical location nodes and containment reasoning, hierarchy consistency validation
- Out-of-scope: Real-world sensor integration
- Success criteria: The agent can distinguish same building or different room from building change
- Risks: Inconsistent hierarchies, premature ontology lock-in
- Likely next phases: 19
- Testing:
  - Run automated tests: `python3 -m pytest tests/ -v` — should include tests for hierarchical node creation, containment reasoning, and hierarchy consistency
  - Manual smoke test: (1) Define nested locations (building → floor → room), (2) Transition between rooms and verify containment reasoning, (3) Verify building-change vs room-change distinctions
  - What to verify: Hierarchical location nodes support containment reasoning; same-building and different-room distinctions work correctly; hierarchy consistency validation catches errors; the ontology remains flexible

## Phase 19 - Multimodal Real-World Ingestion

- Phase number: 19
- Title: Multimodal Real-World Ingestion
- Purpose: Extend the CLI sensor harness into vision, time, and position signals within the same online learning interface.
- Prerequisites: Phase 18 completed and validated
- In-scope: Sensor adapters, synchronized observations, multimodal event logging, transition-aware ingest
- Out-of-scope: Stable long-horizon deployment policy
- Success criteria: Real-world signals enter memory without replacing online learning with pretrained symbolic knowledge
- Risks: Latency, sensor drift, synchronization bugs
- Likely next phases: 20
- Testing:
  - Run automated tests: `python3 -m pytest tests/ -v` — should include tests for sensor adapters, multimodal event synchronization, and transition-aware ingestion
  - Manual smoke test: (1) Feed simulated multimodal signals (vision, time, position), (2) Verify observations enter memory correctly, (3) Check that transition-aware ingest handles concurrent signals
  - What to verify: Sensor adapters normalize diverse inputs into the learning interface; synchronized observations are logged atomically; transition-aware ingest handles timing correctly; no pretrained symbolic knowledge leaks into learned state

## Phase 20 - Stable Real-World Location Monitoring

- Phase number: 20
- Title: Stable Real-World Location Monitoring
- Purpose: Reason online about real-world location changes and nested place identity.
- Prerequisites: Phase 19 completed and validated
- In-scope: Continuous monitoring, correction loop, same-building and same-room distinctions, transition reasoning
- Out-of-scope: Operator tooling and recovery workflows
- Success criteria: The system can reliably reason about room and building change from live multimodal input
- Risks: False transition detection, drift, compounding online errors
- Likely next phases: 21
- Testing:
  - Run automated tests: `python3 -m pytest tests/ -v` — should include tests for continuous monitoring, correction loop, and transition reasoning under live input
  - Manual smoke test: (1) Run continuous monitoring with simulated live multimodal input, (2) Trigger room and building changes, (3) Correct false detections and verify the agent learns from corrections
  - What to verify: Real-time location reasoning is reliable; same-building and same-room distinctions hold under live input; the correction loop recovers from false transitions; drift does not compound over time

## Phase 21 - Long-Horizon Robustness and Operator Tooling

- Phase number: 21
- Title: Long-Horizon Robustness and Operator Tooling
- Purpose: Make the system dependable over long deployments and iterative corrections.
- Prerequisites: Phase 20 completed and validated
- In-scope: Replay tooling, audit views, drift detection, repair workflows, regression suites, correction tools
- Out-of-scope: New sensing modalities
- Success criteria: The system is inspectable, repairable, and trustworthy over long-horizon operation
- Risks: Operational complexity, accidental policy drift, incomplete audit coverage
- Likely next phases: Iterative refinement only
- Testing:
  - Run automated tests: `python3 -m pytest tests/ -v` — should include regression suites, replay validation, drift detection tests, and repair workflow tests
  - Manual smoke test: (1) Run the system for an extended session, (2) Use replay tooling to audit past events, (3) Trigger a drift condition and verify detection, (4) Use repair workflows to correct the drift and confirm recovery
  - What to verify: Replay tooling accurately reconstructs past state; audit views are complete and inspectable; drift detection catches policy changes; repair workflows restore correct behavior; the system remains trustworthy over long-horizon operation

---

## Phase Documentation Standard

When a phase becomes active, `CURRENT_PHASE.md` must be updated to include the following sections in addition to the phase specification:

### Required "How to Run This Phase" Section

Every `CURRENT_PHASE.md` must include a **How to Run This Phase** block near the top containing:

1. **Prerequisites** — Python version, any new dependencies, required prior state
2. **Quick Start** — The exact command(s) to run the phase's functionality
3. **Example Session** — A complete copy-pasteable terminal session showing:
   - What the user types
   - What the agent outputs
   - Annotations explaining what is happening at each step
4. **Running Tests** — The exact test command and expected pass count
5. **What to Check After Running** — Which files to inspect and what they should contain
6. **What Success Looks Like** — A numbered list of observable behaviors that confirm the phase works

This standard ensures that any user encountering the project at any phase can immediately understand what to do, what to expect, and how to verify correctness — without needing prior context or external documentation.
