# Tree-of-Thought Location Agent

A continuously learning agent that begins by anchoring interpretation in location and grows toward a broader synthetic memory-and-attention engine. It learns from observation and correction instead of pretrained knowledge, stores labels as first-class nodes, and now keeps enclosing or overlapping location context active while individual room labels change.

**Current Phase:** 5 — Nested Location Context *(implemented; validation in progress)*

## Quick Start

```bash
# Run the interactive agent
python3 -m location_agent.cli

# Run in quiet/scripting mode
python3 -m location_agent.cli --quiet

# Reset all learned memory
python3 -m location_agent.cli --reset

# Run all automated tests
python3 -B -m unittest discover -s tests -v
```

**Requirements:** Python 3.12+ preferred, stdlib only, no external packages required.

During an interactive session, use `sense /absolute/path/to/file` to route an image, video, or other file through the simulated sensor-learning flow.

For detailed phase-specific instructions and validation steps, see [CURRENT_PHASE.md](CURRENT_PHASE.md).

Repo-local sensor fixtures now live under [media/README.md](media/README.md), and the cross-phase sensor ladder is documented in [MEDIA_PLAN.md](MEDIA_PLAN.md).

## Project Structure

```text
├── README.md
├── CURRENT_PHASE.md
├── PROJECT_ROADMAP.md
├── PROJECT_STATE.json
├── DECISIONS.md
├── VALIDATION.md
├── CHANGELOG.md
├── MEDIA_PLAN.md
├── TODO.md
│
├── media/
│   ├── README.md
│   ├── catalog.json
│   ├── core_images/
│   └── scenarios/
│
├── location_agent/
│   ├── cli.py
│   ├── session.py
│   ├── memory.py
│   ├── models.py
│   └── logging.py
│
├── tests/
│   ├── test_confidence.py
│   ├── test_media.py
│   ├── test_memory.py
│   ├── test_models_phase3.py
│   ├── test_session.py
│   └── test_stress.py
│
└── runtime/
    ├── location_memory.json
    └── agent_events.jsonl
```

## How It Works

1. You provide either a grayscale observation in `[0.0, 1.0]` or a `sense /path/to/media` command.
2. The current Phase 5 sensor preview still matches media files by direct file fingerprint, but the roadmap treats that as a temporary baseline rather than the final perception model.
3. If recognized, it guesses the canonical label and asks for confirmation.
4. If you reuse an existing location label for a new observation, the agent reinforces that same learned location instead of forcing a different name.
5. `contain` teaches enclosing context such as `house -> bedroom`, while `overlap` records co-active locations without duplicating the pair in reverse order.
6. If the same location is confirmed at both ends of a wider scalar range, later values inside that learned span default to the same location unless conflicting evidence appears.
7. `rename` changes the canonical label and keeps the old name as an alias.
8. `alias` adds more names that resolve to the same learned location.
9. `inspect` shows label ids, aliases, provenance-aware model stats, active context, and explicit `contains`, `within`, and `overlaps` relation summaries.

The agent remembers across sessions, including label aliases, rename history, sensor bindings, and location/context scaffolding. Persisted memory is grounded only in explicit user input or direct sensor input.

The current runtime remains location-first on purpose. The long-range roadmap now treats that as the entry curriculum for a broader system that later adds `ObservationBundle`, `ExperienceFrame`, `MemoryUnit`, attention competition, replay, resurfacing, and reconsolidation.

## Perception Architecture

- The long-term sensor contract is one transformed `ObservationBundle` regardless of sensor type.
- Future adapters normalize raw sensor output into the same bundle fields: `bundle_id`, `timestamp`, `adapter_id`, `modality`, `reference_frame`, `pose_estimate`, `motion_estimate`, `sensor_origin`, `regions`, `primitive_features`, `concept_candidates`, `raw_refs`, and `provenance`.
- Later phases wrap each bundle in an `ExperienceFrame` with goals, mode, load, recent winners, and prior residue.
- The planned retained trace is a generic `MemoryUnit` with `content`, `context`, `priority_signals`, `dynamics`, `links`, and `example_refs`.
- The guiding example is explicit in the roadmap: `blue streak across top` and `green streak across bottom` support `sky` and `grass` or `field`, and together can support scene hypotheses such as `park` and `yard`.
- Robot and body-relative sensing still matter, but they now serve a broader synthetic memory-and-attention engine instead of defining the only end state.

## Sensor Media

- The current committed starter pack is image-first and lives in `media/core_images/`.
- Phase 5 adds a committed `house` anchor fixture and reuses the Phase 4 `bedroom` and `living room` fixtures for containment walks.
- `media/catalog.json` lists every committed asset, its provenance, and the scenario ids that depend on it.
- `media/scenarios/` contains ordered validation bundles that describe how fixtures should be used during a phase.
- `MEDIA_PLAN.md` carries the phase-by-phase ladder from committed still images to annotated region fixtures, cue-composition corpora, frame and chunk traces, resurfacing corpora, pose-aware multimodal replays, and operator audit bundles.

## Resetting Memory

- During a session: type `reset` and confirm.
- From the command line: run `python3 -m location_agent.cli --reset`.

Reset clears learned location models, label nodes, concepts, graph edges, and sensor bindings. The event log remains append-only.

## Phase Documentation

`CURRENT_PHASE.md` is the active implementation guide. It describes:

- the current phase goal
- the supported CLI commands
- the expected runtime schema
- the automated and manual validation checklist

For the longer roadmap, see [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md).
