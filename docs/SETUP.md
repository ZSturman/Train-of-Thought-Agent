# Setup and Local Use

This project is intentionally small at the dependency layer. The current implementation runs with Python and the standard library only.

## Requirements

| Requirement | Notes |
| --- | --- |
| Python | Python 3.12+ preferred |
| External packages | None discovered |
| Package manifest | None discovered, no `pyproject.toml`, `setup.py`, or `requirements.txt` |
| Environment variables | None required |
| Deployment files | None discovered |

## Run the Agent

From the repository root:

```bash
python3 -m location_agent.cli
```

Quiet mode is useful for scripted examples and tests:

```bash
python3 -m location_agent.cli --quiet
```

Reset all learned memory and exit:

```bash
python3 -m location_agent.cli --reset
```

Show CLI help:

```bash
python3 -m location_agent.cli --help
```

## Run the Tests

```bash
python3 -B -m unittest discover -s tests -v
```

The current accepted Phase 8 state has 177 automated tests passing.

## What Gets Written Locally

The CLI writes runtime state relative to the current working directory:

```text
runtime/location_memory.json
runtime/agent_events.jsonl
```

`location_memory.json` stores learned models, labels, relations, concepts, sensor bindings, evidence records, and observation bundles. `agent_events.jsonl` is append-only event history for sessions, observations, decisions, feedback, and mutations.

## Isolate Runtime Memory

If you run the CLI from the repository root, it uses the repository's `runtime/` directory. To try a clean session without touching that file, run from a temporary directory and set `PYTHONPATH` to the repository root:

```bash
mkdir -p /tmp/tot-run
cd /tmp/tot-run
PYTHONPATH=/path/to/ToT python3 -m location_agent.cli --quiet
```

That creates `/tmp/tot-run/runtime/` for the test session.

## Basic Interactive Commands

| Command | Use |
| --- | --- |
| `0.25` | Teach or query a scalar observation in the `0.0` to `1.0` range. |
| `sense /absolute/path/to/file` | Learn or recognize a local media file through the sensor flow. |
| `inspect` | Show learned labels, aliases, model stats, relations, and active context. |
| `rename` | Rename an existing canonical label while preserving the old name as an alias. |
| `alias` | Add another name for an existing label. |
| `contain` | Teach an enclosing relation such as `house contains bedroom`. |
| `overlap` | Teach two locations that can be active together. |
| `context` | Show active context for a named location. |
| `concept` | Create a typed concept node. |
| `relate` | Link two concepts with a valid relation. |
| `concepts` | Inspect concept nodes and relations. |
| `reset` | Clear learned memory after confirmation. |
| `quit` | End the session. |

## Try the Included Media Fixtures

The repository includes small generated image fixtures in `media/core_images/`. Use absolute paths when running `sense`:

```text
sense /path/to/ToT/media/core_images/phase04_bedroom_scene.png
```

The first time the agent sees a file, it asks for a label. The next time it sees that same file, it can recognize the stored binding and ask for confirmation.

## Configuration

No external configuration is required. The confidence policy is stored in runtime memory and defaults to:

| Setting | Default |
| --- | --- |
| `kind` | `distance` |
| `tolerance` | `0.05` |
| `guess_threshold` | `0.6` |
| `normalization_decimals` | `6` |
| `outlier_factor` | `3.0` |

These values are part of the current runtime schema and should be changed through code and tests, not by hand-editing runtime files during normal use.
