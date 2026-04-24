# Technical Notes

This file keeps the deeper implementation details out of the main README while still giving maintainers a place to orient quickly.

## Current State

| Area | Current value |
| --- | --- |
| Project phase | Phase 8, Modality-Neutral Observation Bundle |
| Runtime schema | `7` |
| Test runner | `python3 -B -m unittest discover -s tests -v` |
| Last validated suite | 177 tests passing |
| Dependencies | Python standard library only |
| External services | None discovered |
| Environment variables | None required |
| Deployment config | None discovered |

## Runtime Flow

A scalar observation follows this path:

```text
user input -> NormalizedObservation -> MemoryStore.find_nearest()
           -> user confirmation or correction -> persisted memory and event log
```

A sensor file follows this path:

```text
sense /path/to/file -> ImageAdapter.observe()
                    -> ObservationBundle
                    -> SensorObservation compatibility layer
                    -> MemoryStore.bind_sensor_bundle()
                    -> persisted bundle, binding, evidence, and event log
```

The sensor path still uses direct file fingerprints for recognition at the binding layer. Phase 8 makes the input boundary bundle-based so later perception work can add regions, primitive features, and richer adapters without changing every downstream memory path.

## ObservationBundle

`ObservationBundle` is the shared transformed input shape for future sensors. It currently includes:

| Field | Purpose |
| --- | --- |
| `bundle_id` | Stable id for the transformed observation. |
| `timestamp` | Creation time for the bundle. |
| `adapter_id` | The adapter that produced the bundle. |
| `modality` | Input type, such as `image`. |
| `reference_frame` | Optional frame context for later pose-aware sensing. |
| `pose_estimate` | Optional pose estimate. |
| `motion_estimate` | Optional motion estimate. |
| `sensor_origin` | Optional source path or source identity. |
| `regions` | Region descriptors, currently placeholders for Phase 9. |
| `primitive_features` | Low-level percept features, currently placeholders for Phase 9. |
| `concept_candidates` | Candidate concept labels, currently placeholders. |
| `raw_refs` | References back to raw input files or samples. |
| `provenance` | Source marker, limited to `user` or `sensor`. |

The current concrete adapter is `ImageAdapter`, which wraps local file input into this shape. Additional adapters are planned in later phases.

## Persistence Model

Runtime state is stored under `runtime/` by default.

| File | Role |
| --- | --- |
| `runtime/location_memory.json` | Main mutable memory store. |
| `runtime/agent_events.jsonl` | Append-only event log. |

The schema v7 memory store contains:

- `location_models`
- `label_nodes`
- `concept_nodes`
- `graph_edges`
- `sensor_bindings`
- `evidence_records`
- `observation_bundles`
- `confidence_policy`

Migrations are chained inside `MemoryStore._load_or_initialize()`, so older runtime files are upgraded as they load.

## Project Structure

```text
location_agent/
  cli.py       CLI entry point and argument parsing
  session.py   Interactive control loop and command handling
  memory.py    Persistent store, migrations, lookup, and mutations
  models.py    Dataclasses, validation helpers, sensor and bundle contracts
  logging.py   JSONL event logging

tests/
  test_bundle.py
  test_confidence.py
  test_media.py
  test_memory.py
  test_models_phase3.py
  test_session.py
  test_stress.py

media/
  catalog.json
  core_images/
  scenarios/
```

The root continuity documents are part of the project record:

| File | Role |
| --- | --- |
| `CURRENT_PHASE.md` | Active phase guide and validation target. |
| `PROJECT_ROADMAP.md` | Long-range phase plan. |
| `PROJECT_STATE.json` | Machine-readable continuity state. |
| `DECISIONS.md` | Architectural decision record. |
| `VALIDATION.md` | Accepted validation notes and test results. |
| `CHANGELOG.md` | Phase-by-phase implementation history. |
| `MEDIA_PLAN.md` | Cross-phase media ladder and fixture rules. |
| `TODO.md` | Pending work and deferred improvements. |

## Important Constraints

- Persisted memory should come only from explicit user input or direct sensor input.
- The LLM may help communicate, parse, or normalize, but it is not treated as a source of stored truth.
- Runtime persistence is currently single-writer JSON and JSONL.
- Nearest-neighbor scalar lookup currently scans stored models linearly.
- Phase 9 is expected to populate region descriptors and primitive features more meaningfully.

## Useful References

- Current phase: [`../CURRENT_PHASE.md`](../CURRENT_PHASE.md)
- Validation history: [`../VALIDATION.md`](../VALIDATION.md)
- Long-range roadmap: [`../PROJECT_ROADMAP.md`](../PROJECT_ROADMAP.md)
- Media plan: [`../MEDIA_PLAN.md`](../MEDIA_PLAN.md)
- Media fixtures: [`../media/README.md`](../media/README.md)
