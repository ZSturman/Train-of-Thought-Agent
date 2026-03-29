# Current Phase

- Status: in-progress
- Phase number: 4
- Title: First-Class Labels
- Validation result: pending

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

### Phase 4 Commands

- `inspect` — show learned location models with canonical label, aliases, label id, provenance-aware stats, and any active location context
- `rename` — rename an existing canonical label or alias; the old canonical name remains as an alias
- `alias` — add a new alias to an existing label
- `sense /path/to/file` — learn or recognize a simulated sensor input from an image, video, or other file path
- `reset` — clear all learned location models, label nodes, graph edges, concepts, and sensor bindings after confirmation
- `quit` — end the session

### Example Session (Verbose Mode)

```text
========================================================
  Tree-of-Thought Location Agent
  Phase 4: First-Class Labels
========================================================

Enter a grayscale observation (0.0 to 1.0), or 'quit' to exit: 0.25
This is a new observation — I haven't seen this value before.
What location does this represent? Enter a label: kitchen
Learned! 0.250000 → "kitchen"

Enter a grayscale observation (0.0 to 1.0), or 'quit' to exit: 0.29
I recognize this! My guess: "kitchen" (confidence: 60%)
Is this correct? (yes/no): yes
Great — my memory is reinforced.

Enter a grayscale observation (0.0 to 1.0), or 'quit' to exit: rename
Which existing canonical label or alias should I rename? kitchen
What should the new canonical label be? break room
Renamed "kitchen" → "break room". The old name remains as an alias.

Enter a grayscale observation (0.0 to 1.0), or 'quit' to exit: sense /tmp/room.jpg
This image input is new — I don't know its location yet.
What location does this represent? Enter a label: break room
Linked this image input to the existing location "break room".

Enter a grayscale observation (0.0 to 1.0), or 'quit' to exit: alias
Which existing canonical label or alias should receive a new alias? break room
What alias should I add? galley
Added alias "galley" for "break room".

Enter a grayscale observation (0.0 to 1.0), or 'quit' to exit: inspect
--- Learned Location Models ---
  break room           [label-...]  aliases=kitchen, galley  proto=0.270000  spread=0.020000  obs=2  renames=1
-------------------------------
```

### Running Tests

```bash
python3 -B -m unittest discover -s tests -v
```

Expected: 101 automated tests pass.

### What to Check After Running

- `runtime/location_memory.json`
  - `schema_version: 5`
  - `location_models` keyed by `location_id`
  - `label_nodes` keyed by `label_id`
  - `graph_edges`, `concept_nodes`, `sensor_bindings`, and `evidence_records` present for pre-entity location scaffolding
- `runtime/agent_events.jsonl`
  - sensor observations log `observation_kind: "sensor"` with file fingerprint metadata
  - rename and alias mutations log as `label_renamed` and `label_alias_added`
- Existing v1, v2, v3, and v4 memory files auto-migrate to v5
- Reusing an existing label for a new compatible observation reinforces the same location instead of forcing a rename
- Once one location is confirmed at both ends of a wider scalar span, values inside that span are guessed as the same location by default unless conflicting evidence appears
- Renaming a label updates the canonical name while preserving the old name as an alias
- Aliases resolve after restart
- `sense /path/to/file` either recognizes a previously learned location or asks the user what location the file represents
- `inspect` shows canonical label, aliases, label id, prototype, spread, observation count, and rename count

### What Success Looks Like

1. A new observation creates both a location model and a label node.
2. Reusing the same location label for nearby or repeated observations reinforces the existing learned location instead of producing a naming error.
3. If the same location is confirmed across a wider scalar range, later values inside that confirmed span are guessed as the same location by default.
4. `rename` changes the canonical label without losing the old name.
5. `alias` adds another active name for the same label node.
6. Future guesses use the current canonical label.
7. `sense /path/to/file` can learn a location from direct sensor input and recognize it again later.
8. v4 memory upgrades to v5 without losing observation stats.
