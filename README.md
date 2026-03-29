# Tree-of-Thought Location Agent

A continuously learning agent that anchors interpretation in location. It learns from observation and correction — not pretrained knowledge — forming associations between sensory inputs and location labels through an online learning loop.

**Current Phase:** 1 — Persistent Grayscale Location Bootstrap *(completed)*

## Quick Start

```bash
# Run the interactive agent
python3 -m location_agent.cli

# Run in quiet/scripting mode
python3 -m location_agent.cli --quiet

# Reset all learned memory
python3 -m location_agent.cli --reset

# Run all tests
python3 -m pytest tests/ -v
```

**Requirements:** Python 3.12+ (stdlib only — no external packages).

For detailed phase-specific instructions, example sessions, and validation steps, see [CURRENT_PHASE.md](CURRENT_PHASE.md).

## Project Structure

```
├── README.md               ← You are here
├── CURRENT_PHASE.md        ← Active phase spec + how to run it
├── PROJECT_ROADMAP.md      ← 18-phase master plan
├── PROJECT_STATE.json      ← Machine-readable project status
├── DECISIONS.md            ← Key design decisions
├── VALIDATION.md           ← Test and validation records
├── CHANGELOG.md            ← Version history
├── TODO.md                 ← Next steps and tech debt
│
├── location_agent/         ← Core agent package
│   ├── cli.py              ← Public entrypoint (python3 -m location_agent.cli)
│   ├── session.py          ← Interactive session controller
│   ├── memory.py           ← Persistent JSON memory store
│   ├── models.py           ← Data models and normalization
│   └── logging.py          ← Append-only JSONL event logger
│
├── tests/                  ← Automated test suite
│   ├── test_session.py     ← Session controller tests
│   ├── test_memory.py      ← Memory persistence tests
│   └── test_stress.py      ← Stress / scalability tests
│
└── runtime/                ← Learned state (gitignored in production)
    ├── location_memory.json    ← Persistent location memory
    └── agent_events.jsonl      ← Immutable event log
```

## How It Works

1. You provide a grayscale observation (a decimal from 0.0 to 1.0)
2. The agent checks its persistent memory for an exact match
3. If recognized → it guesses the location and asks you to confirm
4. If unknown → it asks you to provide a location label and learns it
5. Every observation, decision, and memory change is logged for inspection

The agent remembers across sessions — restart it and your taught locations persist.

## Resetting Memory

To clear all learned locations:

- **During a session:** Type `reset` at the observation prompt. You will be asked to confirm before anything is deleted.
- **From the command line:** Run `python3 -m location_agent.cli --reset` to clear memory and exit immediately (no confirmation prompt — suitable for scripting).

Only learned location models are cleared. The event log (`runtime/agent_events.jsonl`) is preserved as an immutable audit trail.

## Phase Documentation

Each phase has its full specification and run instructions in [CURRENT_PHASE.md](CURRENT_PHASE.md), which is updated when a new phase becomes active. This file always tells you:

- What the phase does and why
- How to run it (commands, example sessions)
- How to test and validate it
- What success looks like

For the long-term roadmap (18 phases from grayscale bootstrap to real-world spatial reasoning), see [PROJECT_ROADMAP.md](PROJECT_ROADMAP.md).
