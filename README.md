# Tree-of-Thought Location Agent

A small learning agent that remembers places through observation, correction, and inspection.

The project starts with a simple idea: if an agent is going to build useful memory, it should be able to learn from direct experience, accept correction, preserve where its knowledge came from, and show what it thinks it knows. Right now that learning is anchored in locations. You can teach it a numeric observation, connect a media file to a place, rename labels, add aliases, and describe how places relate to each other.

It is not trying to be a finished vision model yet. The current version is a careful scaffold for one, with each sensor input normalized into an `ObservationBundle` before it reaches learning and memory.

| Status | Detail |
| --- | --- |
| Current phase | Phase 8, Modality-Neutral Observation Bundle |
| Last validated state | 177 automated tests passing |
| Next phase | Phase 9, Region Descriptors and Primitive Feature Extraction |
| Runtime style | Local interactive CLI |
| Dependencies | Python standard library only |

## Preview

The agent runs in a terminal. You can give it a value, ask it to sense a local media file, correct its guesses, and inspect what it has learned.

```text
agent online
observation[0.0-1.0|quit]: sense /path/to/bedroom.png
sensor: new image
label: bedroom
observation[0.0-1.0|quit]: sense /path/to/bedroom.png
sensor: recognized image
guess: bedroom (confidence=1.00)
correct?[1/0]: 1
observation[0.0-1.0|quit]: quit
goodbye
```

Behind that short exchange, the project stores a label node, a location model, sensor evidence, and an event log. If the same place later gets renamed or connected to a larger context such as a house, the old label and the enclosing context remain inspectable instead of disappearing.

## What This Project Does

The agent learns location memory from two kinds of input:

- A grayscale-style value between `0.0` and `1.0`, which gives the agent a small controlled observation space.
- A local media file passed through `sense /path/to/file`, which currently uses an image adapter and stores a normalized observation bundle.

When the agent recognizes something, it asks for confirmation. When it is wrong, you can correct it. When a label needs to change, you can rename it while keeping the old name as an alias. When one place contains or overlaps another, you can teach that relationship and later ask the agent to show the active context.

The important part is not that the first observation space is simple. The important part is that the memory is persistent, correctable, and visible.

## Why It Exists

This project explores how a memory system can grow from grounded, inspectable pieces instead of starting as a sealed model that already claims to know the world.

The long-range direction is a synthetic memory-and-attention engine. Location learning is the entry point because it gives the system something concrete to anchor on: a place, a label, a correction, a relationship, and a record of evidence. Later phases expand that into region attention, primitive percepts, experience frames, memory units, replay, resurfacing, and reconsolidation.

One rule carries through the project: persisted memory should come from explicit user input or direct sensor input. The language model may help structure the interaction, but it is not treated as the source of truth.

## Who It Is For

This repository may be useful if you are interested in:

- Learning systems that accept correction instead of treating the first answer as final.
- Memory that can be inspected, renamed, and repaired.
- Small agent architectures that grow in visible phases.
- Sensor and perception work that starts with a stable input contract before adding richer recognition.
- A local Python project that can be read without installing a framework.

For a non-technical reader, the project is easiest to understand as a working notebook for agent memory. For a technical reader, it is a compact Python implementation with tests, schema migrations, media fixtures, and roadmap documents.

## Key Features

| Feature | What it means in practice |
| --- | --- |
| Persistent memory | Learned locations, labels, aliases, relations, sensor bindings, and observation bundles are stored under `runtime/`. |
| Correctable guesses | The agent asks whether a guess is right, then reinforces or corrects memory based on the answer. |
| Label history | Renames preserve the previous canonical name as an alias, so older vocabulary still resolves. |
| Nested context | `contain` can teach relationships such as `house contains bedroom`. |
| Overlapping context | `overlap` can record places that can be active together without forcing one parent-child shape. |
| Concept scaffold | `concept`, `relate`, and `concepts` let the project begin separating named ideas from locations. |
| Sensor preview | `sense /path/to/file` routes local media through an adapter and stores a bundle-backed sensor binding. |
| Inspectable state | `inspect`, `context`, persisted JSON, and JSONL event logs make the learned state visible. |

## Visual Walkthrough

The current visuals are small generated fixtures used by tests and sensor examples. They are not polished screenshots, and that is intentional for now. They keep the project deterministic and easy to run offline while the perception layer is still being built.

| House context | Bedroom | Living room | Unknown scene |
| --- | --- | --- | --- |
| <img alt="Generated house fixture" src="media/core_images/phase05_house_scene.png" width="160"> | <img alt="Generated bedroom fixture" src="media/core_images/phase04_bedroom_scene.png" width="160"> | <img alt="Generated living room fixture" src="media/core_images/phase04_living_room_scene.png" width="160"> | <img alt="Generated unknown fixture" src="media/core_images/phase04_unknown_scene.png" width="160"> |

These files are registered in [`media/catalog.json`](media/catalog.json), explained in [`media/README.md`](media/README.md), and staged through scenario files in [`media/scenarios/`](media/scenarios/). Notes for future screenshots, GIFs, or demo videos live in [`docs/assets/README.md`](docs/assets/README.md).

## What Can I Do With This?

You can run the agent locally, teach it a few places, correct it, and inspect how its memory changes. A simple session might look like this:

1. Teach `0.25` as `kitchen`.
2. Enter `0.253` and confirm that it is still `kitchen`.
3. Rename `kitchen` to a better label if needed.
4. Teach `house`, `bedroom`, and `living room` from the included media fixtures.
5. Use `contain` to say that `house` contains `bedroom` and `living room`.
6. Use `inspect` or `context` to see what the agent now believes.

The current sensor recognition is still a temporary exact-file preview at the binding layer. Phase 8 changes the interface around it, so media now enters as an `ObservationBundle`, but content-based visual understanding is still planned work.

## Quick Start

Requirements: Python 3.12+ is preferred. No external packages are required.

```bash
# Run the interactive agent
python3 -m location_agent.cli

# Run in quiet mode for scripting or tests
python3 -m location_agent.cli --quiet

# Clear learned memory and exit
python3 -m location_agent.cli --reset

# Run the automated test suite
python3 -B -m unittest discover -s tests -v
```

During an interactive session, use `sense /absolute/path/to/file` to route a local media file through the sensor flow.

For fuller setup notes, memory isolation tips, and command examples, see [`docs/SETUP.md`](docs/SETUP.md).

## Technical Notes

The README keeps the technical surface brief so the project remains readable from the outside. These supporting files hold the deeper details:

| Topic | Where to read more |
| --- | --- |
| Setup, local runs, reset behavior, commands | [`docs/SETUP.md`](docs/SETUP.md) |
| Architecture, schema v7, data flow, project structure | [`docs/TECHNICAL.md`](docs/TECHNICAL.md) |
| Common errors and likely fixes | [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md) |
| Contribution workflow | [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) |
| Media fixture and demo capture notes | [`docs/assets/README.md`](docs/assets/README.md) |
| Current phase validation | [`CURRENT_PHASE.md`](CURRENT_PHASE.md) and [`VALIDATION.md`](VALIDATION.md) |
| Long-range roadmap | [`PROJECT_ROADMAP.md`](PROJECT_ROADMAP.md) and [`MEDIA_PLAN.md`](MEDIA_PLAN.md) |

## Contributing

The repository remote is [`https://github.com/ZSturman/Train-of-Thought-Agent.git`](https://github.com/ZSturman/Train-of-Thought-Agent.git).

Before changing behavior, run the test suite and check the current phase notes. The project is intentionally phase-driven, so documentation, media scenarios, and validation notes matter alongside code changes. See [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) for the local workflow.

