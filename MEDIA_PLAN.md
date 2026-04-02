# Sensor Media Plan

This file is the authoritative cross-phase media ladder for the Tree-of-Thought Location Agent.

The long-term progression is:

1. committed still-image fixtures
2. ordered scenario bundles
3. annotated region and cue-composition corpora
4. frame and chunk traces for memory writing
5. activation, replay, and resurfacing corpora
6. pose-aware and multimodal replays
7. long-horizon audit and repair corpora

## ObservationBundle Contract

All future sensor modules normalize raw input into `ObservationBundle` before learning or memory consumes it.

- Fields:
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
- `regions` must be explicit enough to support geometry and salience.
- `primitive_features` must be reusable across modalities and tied back to supporting regions when applicable.
- `concept_candidates` must support multiple labels from the same cue bundle rather than forcing one canonical scene label too early.

## ExperienceFrame and MemoryUnit Bridge

Beginning with the cognitive-engine phases, media must not stop at bundle normalization.

- `ObservationBundle` feeds `ExperienceFrame`.
- `ExperienceFrame` combines the bundle with goals, mode, load, recent winners, and prior residue.
- Chunked `ExperienceFrame` sequences become candidates for `MemoryUnit` write decisions.
- Replay-oriented corpora must support activation, thresholding, resurfacing, inhibition, and reconsolidation checks, not just recognition checks.

## Worked Example

Every future perception-oriented phase should remain compatible with this cue-composition example:

- Primitive percept: `blue streak across top`
- Primitive percept: `green streak across bottom`
- Named concepts supported by the percepts: `sky`, `grass`, `field`
- Composite cue bundle: `blue streak across top + green streak across bottom`
- Scene hypothesis labels supported by the bundle: `park`, `yard`

## Phase 4 - First-Class Labels

- Modality: committed still-image PNG fixtures
- Required pack: `media/core_images/phase04_*` catalog entries for `break room`, `bedroom`, `living room`, `hallway`, `doorway`, `lobby`, and one unknown scene
- Validation scenario: `phase_04_sensor_preview`
- Bridge to next sensing step: reuse the committed image fixtures while adding parent-context media for `house`, `bedroom`, and `living room` in Phase 5

## Phase 5 - Nested Location Context

- Modality: committed still-image containment pack
- Required pack: add a `house` anchor scene plus nested `bedroom` and `living room` scenes that can be taught as co-active context
- Validation scenario: `phase_05_nested_context_walk`
- Bridge to next sensing step: carry the same scenes through alternate contextual variants so Phase 6 can formalize typed concept and relation storage

## Phase 6 - Structured Graph and Concept Scaffold

- Modality: committed still-image context and concept prompts
- Required pack: same-place variants such as `morning`, `night`, and concept prompts that prepare for typed primitive, composite, and scene cue nodes
- Validation scenario: `phase_06_context_concepts`
- Bridge to next sensing step: keep the current exact-file preview intact while preparing for modality-neutral transformed bundles and later `ExperienceFrame` capture

## Phase 7 - Exact-Fingerprint Sensor Preview

- Modality: committed still-image exact-fingerprint recognition set
- Required pack: formalize the current image fixtures as a recognition corpus and add unknown-image prompting cases for regression
- Validation scenario: `phase_07_sensor_preview_regression`
- Bridge to next sensing step: treat direct file fingerprinting as a temporary exact-file preview and replace it with `ObservationBundle` normalization in Phase 8

## Phase 8 - Modality-Neutral Observation Bundle

- Modality: bundle-ready fixtures with metadata sidecars
- Required pack: scenes annotated with `bundle_id`, `timestamp`, `adapter_id`, `raw_refs`, and reference-frame placeholders for every sample
- Validation scenario: `phase_08_observation_bundle_contract`
- Bridge to next sensing step: enrich the bundles with explicit regions, salience, and primitive features in Phase 9

## Phase 9 - Primitive Percept Features and Region Attention

- Modality: annotated region fixtures
- Required pack: scenes with marked top, bottom, left, right, or segmented regions plus salience hints and primitive feature targets
- Validation scenario: `phase_09_region_attention_primitives`
- Bridge to next sensing step: use saved primitive features as the ingredients for cue composition in Phase 10

## Phase 10 - Cue Composition and Hypothesis Support

- Modality: cue-composition corpora
- Required pack: scenes that explicitly realize the worked example, including `blue streak across top`, `green streak across bottom`, `sky`, `grass` or `field`, and the scene hypotheses `park` and `yard`
- Validation scenario: `phase_10_cue_composition_hypotheses`
- Bridge to next sensing step: use composed cue bundles as the substrate for `ExperienceFrame` capture in Phase 11

## Phase 11 - Experience Frame Capture

- Modality: bundle-plus-context traces
- Required pack: scenes paired with active goals, mode tags, load hints, and recent-winner residue annotations
- Validation scenario: `phase_11_experience_frame_capture`
- Bridge to next sensing step: use frame sequences to define chunk boundaries in Phase 12

## Phase 12 - Event Chunk Boundaries

- Modality: ordered frame traces with explicit shifts
- Required pack: short sequences that contain meaningful changes in location, topic, goal, action, or priority
- Validation scenario: `phase_12_event_chunk_boundaries`
- Bridge to next sensing step: treat chunked traces as the write candidates for Phase 13

## Phase 13 - Memory Write Decisions

- Modality: chunk sets with varied write pressure
- Required pack: novel chunks, repeated chunks, weak background chunks, and high-priority chunks that should write with different strength
- Validation scenario: `phase_13_memory_write_decisions`
- Bridge to next sensing step: persist the same generic `MemoryUnit` shape across distinct and repeated traces in Phase 14

## Phase 14 - Instance and Aggregate Traces

- Modality: repeated chunk families with one high-impact outlier
- Required pack: several near-similar sequences that should compress plus one distinctive event that should stay separate
- Validation scenario: `phase_14_instance_aggregate_traces`
- Bridge to next sensing step: feed both instance and aggregate traces into partial-match reactivation in Phase 15

## Phase 15 - Partial Match Reactivation

- Modality: cue-reactivation families
- Required pack: cues that should weakly activate several related traces, not just one exact match
- Validation scenario: `phase_15_partial_match_reactivation`
- Bridge to next sensing step: score the activated traces against each other in Phase 16

## Phase 16 - Attention Competition

- Modality: competing-candidate corpora
- Required pack: activation sets where cue match, goal relevance, novelty, unresolvedness, and inhibition should change the winner
- Validation scenario: `phase_16_attention_competition`
- Bridge to next sensing step: gate the scored candidates through dynamic thresholds in Phase 17

## Phase 17 - Dynamic Workspace Thresholds

- Modality: mode-shifted competition corpora
- Required pack: the same activation sets replayed under relaxed, focused, high-load, and risk-sensitive modes
- Validation scenario: `phase_17_dynamic_workspace_thresholds`
- Bridge to next sensing step: let the winning contents feed the next cue state in Phase 18

## Phase 18 - Thought Chain Residue

- Modality: short chain-forming trace sets
- Required pack: cue families where one winner should bias the next active candidate through residue and neighbor support
- Validation scenario: `phase_18_thought_chain_residue`
- Bridge to next sensing step: keep subthreshold residue alive long enough to explain delayed resurfacing in Phase 19

## Phase 19 - Delayed Resurfacing

- Modality: replay-threshold and delayed-cue corpora
- Required pack: traces that match weakly now but should resurface later after replay or threshold shifts
- Validation scenario: `phase_19_delayed_resurfacing`
- Bridge to next sensing step: add policy-based filtering so some strong traces can still be blocked in Phase 20

## Phase 20 - Policy Inhibition Controls

- Modality: blocked-trace and quarantine corpora
- Required pack: high-value traces that should still be suppressed, delayed, or quarantined under certain modes or costs
- Validation scenario: `phase_20_policy_inhibition_controls`
- Bridge to next sensing step: make recalled traces editable after they pass policy gating in Phase 21

## Phase 21 - Recall Reconsolidation

- Modality: recall-and-update corpora
- Required pack: old traces reactivated under new context so later accessibility, links, or interpretation should change
- Validation scenario: `phase_21_recall_reconsolidation`
- Bridge to next sensing step: let repeated recall and repeated exposure drive broader summary traces in Phase 22

## Phase 22 - Repetition Compression

- Modality: recurring trace families
- Required pack: repeated situations that should collapse into a broader "sense of many times" while preserving exemplar links
- Validation scenario: `phase_22_repetition_compression`
- Bridge to next sensing step: expose higher-level structure as views over the same compressed trace sets in Phase 23

## Phase 23 - Emergent Structure Views

- Modality: structure-rich trace corpora
- Required pack: trace families rich enough to derive relation, entity, affordance, and transition views from shared memory units
- Validation scenario: `phase_23_emergent_structure_views`
- Bridge to next sensing step: stress the same derivation rules against unusual sensing domains in Phase 24

## Phase 24 - Nonhuman Signal Abstraction

- Modality: unusual-sensing and sparse-evidence corpora
- Required pack: synthetic timing distributions, machine-state correlations, sparse cross-channel signatures, or other non-human-like cue families
- Validation scenario: `phase_24_nonhuman_signal_abstraction`
- Bridge to next sensing step: reintroduce pose, motion, and sensor origin as context dimensions in Phase 25

## Phase 25 - Pose and Motion Context

- Modality: pose-aware and motion-aware replays
- Required pack: replay bundles annotated with `reference_frame`, `pose_estimate`, `motion_estimate`, and `sensor_origin` so body-relative context can change activation and thresholds
- Validation scenario: `phase_25_pose_motion_context`
- Bridge to next sensing step: synchronize these contextualized bundles across modalities in Phase 26

## Phase 26 - Multimodal Trace Ingest

- Modality: synchronized multimodal file bundles
- Required pack: image-first bundles augmented with audio, timestamps, position traces, and pose or motion fields that all support the same write and activation path
- Validation scenario: `phase_26_multimodal_trace_ingest`
- Bridge to next sensing step: convert replay bundles into longer live-like streams with drift and corrections for Phase 27

## Phase 27 - Live Cognitive Monitoring

- Modality: long-running live-like multimodal replays
- Required pack: extended replay corpora with drift, noise injection, pose changes, motion changes, resurfacing cases, and repeated corrections across contexts
- Validation scenario: `phase_27_live_cognitive_monitoring`
- Bridge to next sensing step: retain the same replay corpora as auditable operator cases for Phase 28 tooling and repair workflows

## Phase 28 - Operator Audit and Repair

- Modality: audit and replay corpora
- Required pack: long-horizon replay sets, annotated drift cases, trace-repair bundles, and operator review scenarios covering write, activation, inhibition, resurfacing, and reconsolidation history
- Validation scenario: `phase_28_operator_audit`
- Bridge to next sensing step: iterative refinement only; add new corpora without changing `ObservationBundle` unless a new modality is explicitly in scope

## Rules

- Every new phase must add a `Phase Media` section to `CURRENT_PHASE.md`.
- Every new committed asset must be registered in `media/catalog.json`.
- Every phase that starts implementation must add at least one `media/scenarios/*.json` manifest with explicit expected outcomes before the phase is considered in progress.
- Repo-local fixtures are the default. Internet pulls, generated enrichments, or live captures remain optional extras and must not become CI dependencies.
- Any sensing phase after Phase 7 must describe how its media maps into `ObservationBundle`.
- Any phase after Phase 10 must also describe how its media feeds `ExperienceFrame`, chunking, `MemoryUnit` writing, or later activation and replay checks.
- Annotated region fixtures are required for Phases 9 through 10.
- Replay or resurfacing corpora are required for Phases 18 through 22.
- Pose-aware or multimodal replay bundles are required for Phases 25 through 27.
