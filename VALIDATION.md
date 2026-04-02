# Validation

## Phase 8 - Modality-Neutral Observation Bundle

- Status: accepted

### What was tested

- Automated suite via `python3 -B -m unittest discover -s tests -v`
- New bundle tests: ObservationBundle field validation, round-trip serialization, required field rejection, minimal defaults, RegionDescriptor round-trip
- New adapter tests: ImageAdapter properties, observe produces valid bundle, invalid path raises, fingerprint extraction from bundle, sensor observation reconstruction from bundle, two adapters produce same bundle shape, SensorAdapter subclass verification
- New cross-adapter tests: ImageAdapter and MockAudioAdapter share identical bundle dict keys, both are SensorAdapter subclasses
- New persistence tests: schema v7 verification, store and retrieve bundle, bundle persistence across reload, nonexistent bundle returns None, bind_sensor_bundle stores both bundle and binding, v6→v7 migration adds observation_bundles, new store has observation_bundles
- Session banner updated to Phase 8 with adapter-routed sense description
- EventLogger extended with bundle_id and adapter_id fields
- Phase 8 scenario manifest and catalog references created

### What passed

- All 177 automated tests passed (24 new for Phase 8)
- ObservationBundle validates required fields at construction
- ImageAdapter wraps SensorObservation into bundle shape
- Two different adapters (ImageAdapter, MockAudioAdapter) produce identical bundle key sets
- Bundle persists in observation_bundles collection at schema v7
- v6→v7 migration adds observation_bundles without altering existing data
- Session `sense` command routes through adapter → bundle → learning
- EventLogger correctly logs bundle_id and adapter_id
- All 153 Phase 7 regression tests still pass

### What failed

- No automated failures
- No recorded manual failures

### Stress tests or benchmarks

- Stress tests unchanged from Phase 7

### Unresolved issues

- Runtime persistence remains single-writer JSON and JSONL only
- Nearest-neighbor search is still a linear scan over all scalar-backed location models
- Bundle regions and primitive features placeholders not yet populated by adapters (Phase 9 scope)
- Only ImageAdapter exists; additional adapters deferred to later phases

### Disposition

- Accepted — 177 tests pass, all success criteria met, bundle contract enforced, adapter routing verified.

## Phase 7 - Exact-Fingerprint Sensor Preview

- Status: accepted

### What was tested

- Automated suite via `python3 -B -m unittest discover -s tests -v`
- New memory tests: multi-binding persistence, binding update to different location, sensor provenance verification
- New session tests: multi-image learn/recognize, wrong-guess correction, unknown-image label prompting, multiple images same location
- Temporary-preview docstrings added to `SensorObservation` and `SensorBinding`
- Session banner updated with temporary-preview note for `sense` command
- Phase 7 scenario manifest and catalog references created

### What passed

- All 153 automated tests passed (7 new for Phase 7)
- Temporary-preview docstrings on `SensorObservation` and `SensorBinding`
- Session banner updated with temporary-preview note
- Multi-binding persistence verified across reload
- Wrong-guess correction updates binding to new location
- Sensor provenance confirmed as "sensor" source
- Phase 7 scenario manifest and catalog references created

### What failed

- No automated failures
- No recorded manual failures

### Stress tests or benchmarks

- Stress tests unchanged from Phase 6

### Unresolved issues

- Runtime persistence remains single-writer JSON and JSONL only
- Nearest-neighbor search is still a linear scan over all scalar-backed location models
- Phase 6 media fixtures and scenario manifest not yet created (deferred — not blocking Phase 7)

### Disposition

**Accepted** on 2026-04-02. All Phase 7 success criteria met:
- Sensor bindings with `provenance_source: "sensor"` in schema v6
- Fingerprint-keyed bindings linking SHA256 to `location_id`
- Unknown inputs trigger user question instead of invention
- Recognized inputs reuse prior learning with 100% confidence
- Wrong guesses can be corrected, updating the binding target
- Multiple distinct files bound to same or different locations
- Code explicitly documents fingerprint-based sensing as temporary (docstrings + banner)
- Manual quiet-mode smoke run: learn 4 images, re-recognize bedroom, inspect all bindings
- 153 automated tests passed (7 new for Phase 7)

## Phase 6 - Structured Graph and Concept Scaffold

- Status: accepted

### What was tested

- Automated suite via `python3 -B -m unittest discover -s tests -v`
- 146 tests pass (23 new tests for Phase 6)
- New memory tests: concept creation, idempotent re-creation, invalid kind rejection, concept aliasing, concept linking, link deduplication, self-link rejection, invalid relation kind rejection, unknown concept rejection, bidirectional concept relations, inspect_concepts sorted output, concept persistence across reload, all valid concept kinds accepted
- New session tests: `concept` command creates node, rejects invalid kind with retry, detects existing concept; `relate` command links concepts, rejects invalid relation kind with retry, retries on unknown concept; `concepts` shows all nodes with relations; `concepts` on empty store shows "(none)"; updated banner test for Phase 6

### What passed

- All 146 automated tests passed
- Schema v5→v6 migration works (backfills concept_kind="named")
- Relation validation enforces kind+type pairs at storage layer
- Concept CRUD operations persist and reload correctly

### What failed

- No automated failures
- No recorded manual failures

### Stress tests or benchmarks

- Stress tests unchanged from Phase 5 (concept operations add negligible overhead)

### Unresolved issues

- Runtime persistence remains single-writer JSON and JSONL only
- Nearest-neighbor search is still a linear scan over all scalar-backed location models
- Phase 6 media fixtures and scenario manifest not yet created

### Disposition

**Accepted** on 2026-04-02. All Phase 6 success criteria met:
- Typed concept nodes with validated concept_kind field
- Relation-kind validation enforced at storage layer
- Concept CRUD methods fully operational (create, lookup, alias, link, inspect)
- concept/relate/concepts CLI commands integrated
- Schema v5→v6 migration backfills concept_kind on existing nodes
- 146 automated tests pass

## Phase 5 - Nested Location Context

- Status: accepted

### What was tested

- Automated suite via `python3 -B -m unittest discover -s tests -v`
- New memory coverage for containment persistence, overlap canonicalization and deduplication, alias-based relation lookup, self-link no-ops, and active-context traversal across parent and overlap edges
- New session coverage for `contain`, `overlap`, relation-aware quiet `inspect`, active-context emission after nested recognition, duplicate relation no-ops, and updated Phase 5 banner/help text
- New media coverage for `phase_05_nested_context_walk` and the committed `phase05_house_scene` fixture
- Manual quiet-mode smoke run in a temporary runtime directory:

```bash
cd /private/tmp/tot_phase5_validation_clean.3jO3aM
printf '%s\n' \
  'sense /Users/zacharysturman/Downloads/PORTFOLIO/Technology/ToT/media/core_images/phase05_house_scene.png' \
  'house' \
  'sense /Users/zacharysturman/Downloads/PORTFOLIO/Technology/ToT/media/core_images/phase04_bedroom_scene.png' \
  'bedroom' \
  'sense /Users/zacharysturman/Downloads/PORTFOLIO/Technology/ToT/media/core_images/phase04_living_room_scene.png' \
  'living room' \
  'contain' \
  'house' \
  'bedroom' \
  'contain' \
  'house' \
  'living room' \
  'sense /Users/zacharysturman/Downloads/PORTFOLIO/Technology/ToT/media/core_images/phase04_bedroom_scene.png' \
  'yes' \
  'sense /Users/zacharysturman/Downloads/PORTFOLIO/Technology/ToT/media/core_images/phase04_living_room_scene.png' \
  'yes' \
  'inspect' \
  'quit' \
  | env PYTHONPATH=/Users/zacharysturman/Downloads/PORTFOLIO/Technology/ToT python3 -m location_agent.cli --quiet
```

Observed output:

```text
agent online
observation[0.0-1.0|quit]: sensor: new image
label:
observation[0.0-1.0|quit]: sensor: new image
label:
observation[0.0-1.0|quit]: sensor: new image
label:
observation[0.0-1.0|quit]: contain parent: contain child: contains: house -> bedroom
observation[0.0-1.0|quit]: contain parent: contain child: contains: house -> living room
observation[0.0-1.0|quit]: sensor: recognized image
guess: bedroom (confidence=1.00)
correct?[1/0]:
active-context: bedroom, house
observation[0.0-1.0|quit]: sensor: recognized image
guess: living room (confidence=1.00)
correct?[1/0]:
active-context: living room, house
observation[0.0-1.0|quit]: bedroom||label-a1fb1b377558|na|0.000000|0|0|bedroom,house||house|
house||label-17e8b71e1658|na|0.000000|0|0|house|bedroom,living room||
living room||label-6bb445190c4e|na|0.000000|0|0|living room,house||house|
observation[0.0-1.0|quit]: goodbye
```

Persisted runtime summary:

```bash
python3 -c "from pathlib import Path; import json; payload=json.loads(Path('runtime/location_memory.json').read_text()); print({'schema_version': payload['schema_version'], 'location_count': len(payload['location_models']), 'label_count': len(payload['label_nodes']), 'graph_edge_count': len(payload['graph_edges']), 'sensor_binding_count': len(payload['sensor_bindings'])})"
```

```text
{'schema_version': 5, 'location_count': 3, 'label_count': 3, 'graph_edge_count': 2, 'sensor_binding_count': 3}
```

### What passed

- All 116 automated tests passed
- The Phase 5 smoke run showed `house -> bedroom` and `house -> living room` containment being stored explicitly
- Re-recognizing `bedroom` and `living room` emitted `active-context: bedroom, house` and `active-context: living room, house`
- Quiet `inspect` exposed the new relation-aware columns without breaking the existing column prefix

### What failed

- No automated failures
- No recorded manual failures

### Stress tests or benchmarks

- `merge_stress_duration_seconds=6.210291`
- `noisy_stress_duration_seconds=0.007259`
- `stress_duration_seconds=25.000925`

### Additional validation (post-initial smoke run)

- Containment cycle detection implemented and tested: `bedroom contains house` is rejected with `cycle rejected:` message when `house` already contains `bedroom`
- Transitive cycle detection verified: A→B→C with C→A rejected
- On-demand `context` command implemented and tested: `context hallway` shows `active-context: hallway, doorway` when the overlap relation exists
- Standalone overlap-focused smoke run recorded:

```bash
TMPDIR=$(mktemp -d) && cd "$TMPDIR" && printf '%s\n' \
  '0.10' 'hallway' '0.20' 'doorway' \
  'overlap' 'hallway' 'doorway' \
  'context' 'hallway' \
  '0.10' 'yes' 'inspect' 'quit' \
  | env PYTHONPATH=/path/to/ToT python3 -m location_agent.cli --quiet
```

```text
agent online
observation[0.0-1.0|quit]: where am i
label: observation[0.0-1.0|quit]: where am i
label: observation[0.0-1.0|quit]: overlap first: overlap second: overlaps: hallway <-> doorway
observation[0.0-1.0|quit]: context for: active-context: hallway, doorway
observation[0.0-1.0|quit]: guess: hallway (confidence=1.00)
correct?[1/0]: active-context: hallway, doorway
observation[0.0-1.0|quit]: doorway||...|doorway,hallway|||hallway
hallway||...|hallway,doorway|||doorway
observation[0.0-1.0|quit]: goodbye
```

- All 123 automated tests pass after additions (cycle detection, context command, overlap validation)

### Unresolved issues

- Runtime persistence remains single-writer JSON and JSONL only
- Nearest-neighbor search is still a linear scan over all scalar-backed location models

### Disposition

**Accepted** on 2026-04-01. All Phase 5 success criteria met:
- Containment edges are stored explicitly and survive restarts
- Overlap edges are canonicalized and deduplicated
- Active context can contain more than one location node
- Sibling transitions preserve the enclosing location
- Containment cycles are rejected with a clear error
- On-demand `context` command surfaces active context for any named location
- 123 automated tests pass

- pending

## Phase 4 - First-Class Labels

- Status: accepted
- Disposition: accepted

### What was tested

- Automated suite via `python3 -B -m unittest discover -s tests -v`
- Regression coverage for label nodes, rename and alias behavior, sensor binding, learned-span inference, migrations, provenance, and the Phase 4 media ladder
- Refreshed manual quiet-mode smoke run in a temporary runtime directory:

```bash
cd /private/tmp/tot_phase4_validation_clean.ut06cA
printf '%s\n' \
  '0.10' \
  'Point one' \
  '0.30' \
  'Point one' \
  'yes' \
  '0.28' \
  'yes' \
  'rename' \
  'Point one' \
  'Point one north' \
  'alias' \
  'Point one north' \
  'P1' \
  'sense /Users/zacharysturman/Downloads/PORTFOLIO/Technology/ToT/media/core_images/phase04_break_room_scene.png' \
  'break room' \
  'sense /Users/zacharysturman/Downloads/PORTFOLIO/Technology/ToT/media/core_images/phase04_break_room_scene.png' \
  'yes' \
  'inspect' \
  'quit' \
  | env PYTHONPATH=/Users/zacharysturman/Downloads/PORTFOLIO/Technology/ToT python3 -m location_agent.cli --quiet
```

Observed output:

```text
agent online
observation[0.0-1.0|quit]: where am i
label: observation[0.0-1.0|quit]: where am i
label: outlier: far from Point one @ 0.100000. merge?[yes/no]
correct?[1/0]: observation[0.0-1.0|quit]: guess: Point one (confidence=1.00)
correct?[1/0]: observation[0.0-1.0|quit]: rename from: rename to: renamed: Point one -> Point one north
observation[0.0-1.0|quit]: alias for: alias name: alias-added: P1 -> Point one north
observation[0.0-1.0|quit]: sensor: new image
label:
observation[0.0-1.0|quit]: sensor: recognized image
guess: break room (confidence=1.00)
correct?[1/0]:
observation[0.0-1.0|quit]: break room||label-c470df02ab74|na|0.000000|0|0|break room|||
Point one north|Point one,P1|label-c324cda7345e|0.226667|0.089938|3|1|Point one north|||
observation[0.0-1.0|quit]: goodbye
```

Persisted runtime summary:

```bash
python3 -c "from pathlib import Path; import json; payload=json.loads(Path('runtime/location_memory.json').read_text()); print({'schema_version': payload['schema_version'], 'location_count': len(payload['location_models']), 'label_count': len(payload['label_nodes']), 'graph_edge_count': len(payload['graph_edges']), 'sensor_binding_count': len(payload['sensor_bindings'])})"
```

```text
{'schema_version': 5, 'location_count': 2, 'label_count': 2, 'graph_edge_count': 0, 'sensor_binding_count': 1}
```

### What passed

- All 116 automated tests passed during the closeout run
- The refreshed manual smoke validated:
  - learned-span default inference from `0.10`, `0.30`, then `0.28`
  - canonical rename from `Point one` to `Point one north`
  - alias persistence via `P1`
  - exact-fingerprint sensor learning and re-recognition for the committed break-room image

### Edge cases

- Active canonical names and aliases remain globally unique across label nodes
- Reusing an existing label reinforces that same location instead of creating a naming conflict
- Values inside a confirmed scalar span are matched by default unless conflicting evidence appears
- Rename preserves the old canonical name as an alias by default
- Alias lookup is case-insensitive while preserving stored casing
- Wrong-guess correction keeps the location-model identity while changing the canonical label
- Sensor recognition still uses direct file fingerprints only; no LLM-derived facts are persisted

### Unresolved issues carried forward

- Shared labels across multiple distinct locations remain out of scope until the later ambiguity phase
- Runtime persistence remains single-writer JSON and JSONL only
- Nearest-neighbor search is still a linear scan over all scalar-backed location models

## Phase 3 - Multi-Observation Location Models

- Status: accepted
- Disposition: accepted
- Notes:
  - Phase 3 was accepted before Phase 4 implementation started.
  - Its automated behaviors remain covered by the later regression suites.

## Phase 2 - Noisy Scalar Matching and Confidence Calibration

- Status: accepted
- Disposition: accepted

## Phase 1 - Persistent Grayscale Location Bootstrap

- Status: accepted
- Disposition: accepted
