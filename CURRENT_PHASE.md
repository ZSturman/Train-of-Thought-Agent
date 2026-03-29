# Current Phase

- Status: in-progress
- Phase number: 2
- Title: Noisy Scalar Matching and Confidence Calibration
- Validation result: pending

---

## How to Run This Phase

### Prerequisites

- Python 3.12+ (stdlib only — no external packages required)
- A writable local project directory

### Quick Start

```bash
cd /path/to/ToT
python3 -m location_agent.cli
```

For minimal/scripting output (original terse mode):

```bash
python3 -m location_agent.cli --quiet
```

For usage help:

```bash
python3 -m location_agent.cli --help
```

### Example Session (Verbose Mode)

```
========================================================
  Tree-of-Thought Location Agent
  Phase 2: Noisy Scalar Matching and Confidence Calibration
========================================================

This agent learns to associate grayscale observations
with location labels. It remembers what you teach it
and tries to guess on future observations.

HOW IT WORKS
  1. You enter a grayscale value (a decimal from 0.0 to 1.0).
  2. If the agent recognizes it (exact or close match),
     it guesses the location and asks you to confirm.
  3. If the agent is unsure, it shows its best guess
     but asks you to confirm or provide a label.
  4. If the agent does NOT recognize it, it asks you
     to provide a location label so it can learn.

Type 'quit' at any time to exit.
--------------------------------------------------------

Enter a grayscale observation (0.0 to 1.0), or 'quit' to exit: 0.25
This is a new observation — I haven't seen this value before.
What location does this represent? Enter a label: kitchen
Learned! 0.250000 → "kitchen"

Enter a grayscale observation (0.0 to 1.0), or 'quit' to exit: 0.253
I recognize this! My guess: "kitchen" (confidence: 97%)
Is this correct? (yes/no): yes
Great — my memory is reinforced.

Enter a grayscale observation (0.0 to 1.0), or 'quit' to exit: 0.90
This is a new observation — I haven't seen this value before.
What location does this represent? Enter a label: lobby
Learned! 0.900000 → "lobby"

Enter a grayscale observation (0.0 to 1.0), or 'quit' to exit: quit

--- Session Summary ---
  Observations entered : 3
  New locations learned : 2
  Correct guesses      : 1
  Wrong guesses        : 0
-----------------------
goodbye
```

### Running Tests

```bash
python3 -m pytest tests/ -v
```

Expected: 30 tests pass (16 confidence/distance, 3 memory, 9 session, 2 stress).

### What to Check After Running

- `runtime/location_memory.json` — Should contain `schema_version: 2`, `tolerance` in confidence_policy, and your learned observations
- `runtime/agent_events.jsonl` — Should contain logged events for the session
- The agent should recall observations across restarts
- Noisy observations (e.g. 0.253 after learning 0.25) should produce a confident guess with < 100% confidence
- Far observations (e.g. 0.90 after only learning 0.25) should trigger the unknown path

### What Success Looks Like

1. A new observation value triggers a prompt asking you to label the location
2. Re-entering the same value produces a confident guess (confidence 100%)
3. Entering a *similar* value (within tolerance of 0.05) produces a confident guess with reduced confidence
4. Entering a value just within tolerance produces an uncertain guess that asks for confirmation
5. Entering a truly different value triggers the unknown path
6. The near-collision guard warns when learning a new observation close to an existing one
7. Confirming with "yes" reinforces memory; "no" triggers a relabel or new-label path
8. Quitting shows a summary of what happened in the session
9. Restarting the agent and entering a previously learned value still produces the correct guess
10. Schema v1 memory files are transparently migrated to v2 on load

---

## 1. Phase Goal

Build the first runnable agent: it accepts one grayscale observation in `[0.0, 1.0]`, normalizes it, checks persistent memory, guesses only on confident exact matches, otherwise asks `where am i`, accepts feedback `1` or `0`, stores or corrects the location label persistently, and logs every observation, guess, confidence, feedback, and memory mutation.

## 2. Why This Phase Exists

Every later capability depends on a reliable online learning loop with persistence, correction, and inspectable logs. Without this phase, later ambiguity handling, episodes, transitions, and real-world monitoring would rest on an unstable base.

## 3. Prerequisites

- Python 3.12.4 available locally
- Writable local project directory
- No prior implementation dependencies

## 4. Scope

### In-scope

- Interactive CLI loop
- Scalar observation validation in `[0.0, 1.0]`
- Exact normalized lookup using six decimal places
- Persistent JSON memory in `runtime/location_memory.json`
- Append-only JSONL event logging in `runtime/agent_events.jsonl`
- Correction flow for wrong guesses
- Unit, regression, and stress tests
- Tracking artifact initialization and updates

### Out-of-scope

- Noisy matching
- Multi-observation location models
- First-class labels
- Entities, relations, episodes, actions, affordances, composite events
- Real-world sensing

## 5. Architecture

- `location_agent.models`: observation and location dataclasses plus normalization helpers
- `location_agent.memory`: persistent store for lookup, learn, correction, and counter updates
- `location_agent.logging`: append-only JSONL event logger
- `location_agent.session`: interactive session controller with injectable I/O
- `location_agent.cli`: public entrypoint for `python3 -m location_agent.cli`

The runtime state remains outside the tracking artifacts so the project files can describe status while the runtime files store learned memory and logs.

## 6. Data Structures

- `NormalizedObservation`
  - `raw_input`
  - `value`
  - `key`
- `LocationRecord`
  - `location_id`
  - `observation_key`
  - `observation_value`
  - `label`
  - `observation_count`
  - `guess_count`
  - `correct_count`
  - `incorrect_count`
  - `first_seen_at`
  - `last_seen_at`
- Memory JSON schema
  - `schema_version`
  - `created_at`
  - `updated_at`
  - `confidence_policy`
  - `locations_by_observation`
- Event JSONL schema
  - `schema_version`
  - `timestamp`
  - `event_type`
  - `session_id`
  - `observation_key`
  - `observation_value`
  - `guessed_label`
  - `confidence`
  - `feedback`
  - `mutation_kind`
  - `old_record`
  - `new_record`
  - `notes`

## 7. Interfaces

- Public CLI: `python3 -m location_agent.cli`
- Flags: `--quiet` or `-q` for minimal scripting output
- Verbose prompts (default)
  - Observation: `Enter a grayscale observation (0.0 to 1.0), or 'quit' to exit: `
  - Feedback: `Is this correct? (yes/no): ` — accepts yes/no/y/n/1/0
  - Label: `What location does this represent? Enter a label: `
- Verbose output messages
  - Welcome banner with phase info, instructions, and available commands
  - `I recognize this! My guess: "<label>" (confidence: 100%)`
  - `This is a new observation — I haven't seen this value before.`
  - `Learned! <key> → "<label>"` / `Great — my memory is reinforced.` / `Updated! Corrected "<old>" → "<new>"`
  - Session summary on exit (observations, learned, correct, wrong)
  - `goodbye`
- Quiet prompts (--quiet)
  - `observation[0.0-1.0|quit]: `
  - `correct?[1/0]: `
  - `label: `
- Quiet output messages
  - `agent online`
  - `guess: <label> (confidence=1.00)`
  - `where am i`
  - `goodbye`

## 8. Implementation Plan

1. Create tracking artifacts and set Phase 1 as active.
2. Implement stdlib-only package modules.
3. Normalize observations before lookup or persistence.
4. Log observations, decisions, feedback, and memory mutations.
5. Add invalid input handling and graceful `quit`.
6. Add unit, regression, and stress tests.
7. Validate using automated tests and a manual CLI smoke sequence.
8. Update all tracking artifacts to the validated result.

## 9. Files To Create Or Modify

- `PROJECT_ROADMAP.md`
- `PROJECT_STATE.json`
- `CURRENT_PHASE.md`
- `TODO.md`
- `DECISIONS.md`
- `VALIDATION.md`
- `CHANGELOG.md`
- `location_agent/__init__.py`
- `location_agent/models.py`
- `location_agent/memory.py`
- `location_agent/logging.py`
- `location_agent/session.py`
- `location_agent/cli.py`
- `tests/test_memory.py`
- `tests/test_session.py`
- `tests/test_stress.py`

## 10. Tests

- Unknown observation asks for label and persists it
- Known observation guesses with confidence `1.00`
- Wrong guess triggers correction and updates memory
- Restart preserves learned records
- Invalid observation, label, and feedback paths reprompt correctly
- Normalization regression for `0.25` and `0.250000`
- Automated suite result: 6 tests passed
- Manual smoke result: passed using the public CLI entrypoint

## 11. Benchmarks / Stress Tests

- Learn at least 1000 unique normalized observations
- Reload the store and sample lookups without schema corruption
- Observed duration during automated validation: `2.549653` seconds

## 12. Expected Behavior

- A new observation triggers `where am i` and persists the provided label
- A repeated known observation triggers a guess with confidence `1.00`
- Wrong feedback triggers a relabel of the same observation key
- Each memory change is recorded in the event log with before or after state

## 13. Known Limitations

- Matching is exact after six-decimal normalization
- Labels are plain strings in this phase
- Different observation keys with the same label are not merged
- No entities, actions, relations, episodes, or transitions yet
- The runtime store assumes a single local writer

## 14. Exit Criteria

- CLI loop runs end to end without edits
- Learned observations persist across restarts
- Every observation cycle logs observation, decision, confidence, and feedback
- Every create or correction produces a memory-mutation log record
- Unit, regression, and stress validations pass
- Tracking artifacts match the actual implementation and validation state

All exit criteria are satisfied for Phase 1.

## 15. Tracking Artifact Updates

- `PROJECT_STATE.json` marks Phase 1 completed and Phase 2 as the next recommended phase
- `VALIDATION.md` records the accepted automated and manual validation results
- `CHANGELOG.md` includes the implementation and validation entry
- `TODO.md` now reflects post-phase waiting state plus next-phase preparation items
