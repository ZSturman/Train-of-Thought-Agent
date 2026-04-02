# Current Phase

- Status: accepted
- Phase number: 8
- Title: Modality-Neutral Observation Bundle
- Validation result: accepted — 177 tests pass, all success criteria met
- Next phase: 9 — Region Descriptors & Primitive Feature Extraction

---

## How to Run This Phase

### Prerequisites

- Python 3.12+ preferred
- Writable local project directory
- No external dependencies

### Quick Start

```bash
cd /path/to/ToT
python3 -m location_agent.cli
```

Quiet mode:

```bash
python3 -m location_agent.cli --quiet
```

Reset and exit:

```bash
python3 -m location_agent.cli --reset
```

### Phase 8 Focus

Phase 8 defines and adopts one transformed observation interface (`ObservationBundle`) that every
future sensor module must emit. The existing `sense /path/to/file` command still works, but now
routes through an `ImageAdapter` that normalizes the raw sensor input into the standard bundle shape
before it reaches learning or memory. File-identity fingerprints are preserved as `raw_refs` but are
no longer the primary recognition mechanism at the interface boundary.

### Phase 8 Commands

All Phase 7 commands remain. The `sense` command now routes through the adapter layer:

- `sense /path/to/file` — learn or recognize a location via adapter → bundle → learning
- `concept` / `relate` / `concepts` — concept graph management (from Phase 6)
- `context` — show active location context (from Phase 5)
- `contain` / `overlap` — teach location relations (from Phase 5)
- `inspect` — show learned models, labels, relations, and stats
- `rename` / `alias` — label management
- `reset` — clear all memory after confirmation
- `quit` — end the session

### Example Session (Quiet Mode)

```text
agent online
observation[0.0-1.0|quit]: sense /path/to/bedroom.png
sensor: new image (via image-adapter)
label: bedroom
sensor: learned "bedroom" from image
observation[0.0-1.0|quit]: sense /path/to/bedroom.png
sensor: recognized image (via image-adapter)
guess: bedroom (confidence=1.00)
correct?[1/0]: 1
active-context: bedroom
observation[0.0-1.0|quit]: quit
goodbye
```

### Running Tests

```bash
python3 -B -m unittest discover -s tests -v
```

### What to Check After Running

- `runtime/location_memory.json`
  - `schema_version: 7`
  - `sensor_bindings` contains fingerprint-keyed bindings with `provenance_source: "sensor"`
  - Each binding links a SHA256 fingerprint to exactly one `location_id`
- The `sense` command routes through `ImageAdapter` → `ObservationBundle` → learning
- `ObservationBundle` fields include: `bundle_id`, `timestamp`, `adapter_id`, `modality`,
  `reference_frame`, `pose_estimate`, `motion_estimate`, `sensor_origin`, `regions`,
  `primitive_features`, `concept_candidates`, `raw_refs`, `provenance`
- Two different adapters produce the same bundle shape
- Bundle provenance and raw references survive normalization
- Existing sensor bindings are preserved through schema migration

### What Success Looks Like

1. The exact-file preview remains available and clearly documented as temporary.
2. Sensor bindings rely on direct file fingerprints only in this phase.
3. Unknown inputs trigger a user question instead of invention.
4. Recognized inputs reuse prior learning.
5. Regression tests cover multi-image learning, recognition, correction, and unknown prompting.
6. Documentation markers clarify that Phase 8 replaces file identity with content-based perception.
