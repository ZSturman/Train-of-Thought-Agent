# Tree-of-Thought Location Agent

A continuously learning agent that anchors interpretation in location. It learns from observation and correction instead of pretrained knowledge, stores labels as first-class nodes, and now treats reused location labels as reinforcement of the same place instead of a naming error.

**Current Phase:** 4 — First-Class Labels *(implemented; validation in progress)*

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

## Project Structure

```text
├── README.md
├── CURRENT_PHASE.md
├── PROJECT_ROADMAP.md
├── PROJECT_STATE.json
├── DECISIONS.md
├── VALIDATION.md
├── CHANGELOG.md
├── TODO.md
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
2. The agent matches scalar observations against learned location models and matches media files by direct file fingerprint.
3. If recognized, it guesses the canonical label and asks for confirmation.
4. If you reuse an existing location label for a new observation, the agent reinforces that same learned location instead of forcing a different name.
5. If the same location is confirmed at both ends of a wider scalar range, later values inside that learned span default to the same location unless conflicting evidence appears.
6. `rename` changes the canonical label and keeps the old name as an alias.
7. `alias` adds more names that resolve to the same learned location.
8. `inspect` shows label ids, aliases, provenance-aware model stats, and location context scaffolding.

The agent remembers across sessions, including label aliases, rename history, sensor bindings, and location/context scaffolding. Persisted memory is grounded only in explicit user input or direct sensor input.

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
