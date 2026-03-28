# Project Roadmap

This file is the master planning layer for the project. It is the authoritative long-range roadmap unless superseded by a documented replan.

## End-State Vision

A continuously learning, inspectable agent that anchors interpretation in location, learns from observation and correction instead of pretrained world knowledge, forms labels, entities, relations, episodes, affordances, and composite events online, and ultimately reasons about real-world location change at the granularity of doorway, hallway, room, and building.

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

## Phase 4 - First-Class Labels

- Phase number: 4
- Title: First-Class Labels
- Purpose: Promote labels into explicit nodes rather than plain strings stored directly on locations.
- Prerequisites: Phase 3 completed and validated
- In-scope: Label nodes, label-location edges, rename history, alias handling
- Out-of-scope: Scene entities, ambiguity resolution policies
- Success criteria: Labels exist independently from single observations and can be reused or refined later
- Risks: Migration bugs, identity mismatches between labels and locations
- Likely next phases: 5, 9

## Phase 5 - Minimal Scene Entities

- Phase number: 5
- Title: Minimal Scene Entities
- Purpose: Add simple entity observations inside the simulator without hardcoded world structure.
- Prerequisites: Phase 4 completed and validated
- In-scope: Entity nodes, observed-at-location links, simple entity logging and tests
- Out-of-scope: Rich relations, affordances, action semantics
- Success criteria: The agent can learn that locations are associated with observed entities from experience
- Risks: Confusing labels with entities, overcomplicating the simulator too early
- Likely next phases: 6

## Phase 6 - Location-Conditioned Entity Inference

- Phase number: 6
- Title: Location-Conditioned Entity Inference
- Purpose: Make interpretation of cues depend on location context.
- Prerequisites: Phase 5 completed and validated
- In-scope: Entity likelihood by location, context-sensitive retrieval, tests for same cue in different places
- Out-of-scope: Full relation graph semantics, temporal episode modeling
- Success criteria: The same sensory cue can lead to different inferred entities depending on location context
- Risks: Brittle priors, leaking assumptions into learned inference
- Likely next phases: 7, 8

## Phase 7 - Relations Graph

- Phase number: 7
- Title: Relations Graph
- Purpose: Introduce explicit learned relations such as contains, near, connected-to, and co-occurs.
- Prerequisites: Phase 6 completed and validated
- In-scope: Inspectable graph edges, relation queries, relation mutation logging
- Out-of-scope: Episodic sequencing, clarification workflows
- Success criteria: Relation-based retrieval is possible and explainable using learned graph edges
- Risks: Edge explosion, inconsistent relation semantics
- Likely next phases: 8

## Phase 8 - Episodic Memory and Temporal Sequences

- Phase number: 8
- Title: Episodic Memory and Temporal Sequences
- Purpose: Store ordered experiences and recall recent sequences.
- Prerequisites: Phase 7 completed and validated
- In-scope: Episode records, temporal ordering, replay support, recency-aware retrieval
- Out-of-scope: Clarification policy, composite event abstraction
- Success criteria: The agent can store and inspect ordered sequences of observations and transitions
- Risks: Storage growth, unclear episode boundaries
- Likely next phases: 9, 13

## Phase 9 - Ambiguity Detection and Clarification

- Phase number: 9
- Title: Ambiguity Detection and Clarification
- Purpose: Detect when current evidence supports multiple plausible interpretations and ask clarifying questions.
- Prerequisites: Phases 4 and 8 completed and validated
- In-scope: Ambiguity state tracking, clarification prompts, unresolved-memory support
- Out-of-scope: Subtype taxonomies, affordances, actions
- Success criteria: The agent asks for clarification instead of silently overcommitting when evidence is ambiguous
- Risks: Excessive questioning, poor ambiguity thresholds
- Likely next phases: 10

## Phase 10 - Category Refinement and Subtype Learning

- Phase number: 10
- Title: Category Refinement and Subtype Learning
- Purpose: Support broad labels and later subtype distinctions through repeated experience and correction.
- Prerequisites: Phase 9 completed and validated
- In-scope: Category and subtype links, refinement logic, correction-driven updates
- Out-of-scope: Affordances, actions
- Success criteria: Shared labels can coexist with more precise subtype distinctions when ambiguity is clarified
- Risks: Premature category splitting, unstable refinements
- Likely next phases: 11

## Phase 11 - Affordances

- Phase number: 11
- Title: Affordances
- Purpose: Learn what locations or entities enable without hardcoding symbolic knowledge.
- Prerequisites: Phases 5 and 10 completed and validated
- In-scope: Affordance nodes or edges, affordance evidence, retrieval and inspection
- Out-of-scope: Executable action primitives
- Success criteria: The agent can represent learned affordances grounded in experience
- Risks: Sparse evidence, confusing observed outcomes with possibilities
- Likely next phases: 12

## Phase 12 - Action Primitives in Simulation

- Phase number: 12
- Title: Action Primitives in Simulation
- Purpose: Add a minimal action loop and learn from action outcomes.
- Prerequisites: Phase 11 completed and validated
- In-scope: Small action set, outcome logging, correction-driven outcome updates
- Out-of-scope: Composite event discovery, real-world sensing
- Success criteria: Action outcomes modify learned state through the same online learning principles
- Risks: Credit assignment mistakes, simulator complexity creep
- Likely next phases: 13

## Phase 13 - Composite Event Discovery

- Phase number: 13
- Title: Composite Event Discovery
- Purpose: Let higher-level events emerge from repeated lower-level temporal structure.
- Prerequisites: Phases 8 and 12 completed and validated
- In-scope: Repeated-sequence clustering, composite event records, inspection and validation tools
- Out-of-scope: Spatial hierarchy, real-world deployment
- Success criteria: Stable composite events can be discovered without hardcoded event labels
- Risks: Over-grouping, under-grouping, opaque abstractions
- Likely next phases: 14

## Phase 14 - Spatial Transitions and Doorway-Hallway Reasoning

- Phase number: 14
- Title: Spatial Transitions and Doorway-Hallway Reasoning
- Purpose: Learn transitions, room boundaries, and doorway or hallway distinctions in simulation.
- Prerequisites: Phases 8 and 13 completed and validated
- In-scope: Transition detection, boundary-state modeling, hallway-vs-room reasoning
- Out-of-scope: Building hierarchy, multimodal sensing
- Success criteria: The agent detects room changes, doorway traversal, and transition structure
- Risks: Noisy boundary states, unclear transition segmentation
- Likely next phases: 15

## Phase 15 - Room and Building Hierarchy

- Phase number: 15
- Title: Room and Building Hierarchy
- Purpose: Add nested location reasoning for buildings, floors, rooms, and hallways.
- Prerequisites: Phase 14 completed and validated
- In-scope: Hierarchical location nodes and containment reasoning, hierarchy consistency validation
- Out-of-scope: Real-world sensor integration
- Success criteria: The agent can distinguish same building or different room from building change
- Risks: Inconsistent hierarchies, premature ontology lock-in
- Likely next phases: 16

## Phase 16 - Multimodal Real-World Ingestion

- Phase number: 16
- Title: Multimodal Real-World Ingestion
- Purpose: Add vision, time, and position signals to the same online learning interface.
- Prerequisites: Phase 15 completed and validated
- In-scope: Sensor adapters, synchronized observations, multimodal event logging, transition-aware ingest
- Out-of-scope: Stable long-horizon deployment policy
- Success criteria: Real-world signals enter memory without replacing online learning with pretrained symbolic knowledge
- Risks: Latency, sensor drift, synchronization bugs
- Likely next phases: 17

## Phase 17 - Stable Real-World Location Monitoring

- Phase number: 17
- Title: Stable Real-World Location Monitoring
- Purpose: Reason online about real-world location changes and nested place identity.
- Prerequisites: Phase 16 completed and validated
- In-scope: Continuous monitoring, correction loop, same-building and same-room distinctions, transition reasoning
- Out-of-scope: Operator tooling and recovery workflows
- Success criteria: The system can reliably reason about room and building change from live multimodal input
- Risks: False transition detection, drift, compounding online errors
- Likely next phases: 18

## Phase 18 - Long-Horizon Robustness and Operator Tooling

- Phase number: 18
- Title: Long-Horizon Robustness and Operator Tooling
- Purpose: Make the system dependable over long deployments and iterative corrections.
- Prerequisites: Phase 17 completed and validated
- In-scope: Replay tooling, audit views, drift detection, repair workflows, regression suites, correction tools
- Out-of-scope: New sensing modalities
- Success criteria: The system is inspectable, repairable, and trustworthy over long-horizon operation
- Risks: Operational complexity, accidental policy drift, incomplete audit coverage
- Likely next phases: Iterative refinement only

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
