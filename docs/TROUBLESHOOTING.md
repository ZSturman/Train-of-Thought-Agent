# Troubleshooting

Most issues in the current project come from input shape, working directory, or label and relation rules. This page collects the common ones.

## Common Issues

| Symptom | Likely cause | What to do |
| --- | --- | --- |
| `invalid observation: enter a number between 0.0 and 1.0` | The scalar input was blank, non-numeric, or outside the supported range. | Enter a decimal such as `0.25`, or use a command such as `sense /path/to/file`. |
| `sensor path not found` | The file path passed to `sense` does not exist from the current machine. | Use an absolute path, or confirm the file exists before running the command. |
| `sensor path is not a file` | The path points to a directory. | Pass a specific file path from `media/core_images/` or another local file. |
| `label "..." is already in use` | Canonical labels and aliases are globally unique in the current phase. | Choose a different label, or reuse the existing label if you mean the same location. |
| `cycle rejected` | A `contain` command would create a containment loop. | Keep containment directional, such as `house contains bedroom`, and avoid making the child contain the parent. |
| A learned place is missing | The CLI may have been run from a different working directory, which creates a different `runtime/` directory. | Check where you launched the command. The runtime path is relative to the current working directory. |
| Tests cannot import `location_agent` from a temporary directory | The repository root is not on `PYTHONPATH`. | Run tests from the repository root, or set `PYTHONPATH=/path/to/ToT`. |

## Sensor Recognition Looks Too Exact

That is expected right now. The current sensor preview still recognizes files through a direct file fingerprint at the binding layer. Phase 8 routes the input through `ImageAdapter -> ObservationBundle -> learning`, but content-based image understanding is not complete yet.

If a copied or modified image does not match a previously learned image, teach it as a new input or wait for the later perception phases that add richer content features.

## Resetting Memory

From inside a session:

```text
reset
```

From the command line:

```bash
python3 -m location_agent.cli --reset
```

Reset clears learned models, labels, concepts, graph edges, sensor bindings, evidence records, and observation bundles from `location_memory.json`. The event log remains append-only.

## Tests

Run the full suite from the repository root:

```bash
python3 -B -m unittest discover -s tests -v
```

If tests fail after a documentation-only change, check whether runtime files were edited accidentally. The docs refresh should not change public APIs, schema behavior, tests, or CLI behavior.

## When in Doubt

Read these files in this order:

1. [`../CURRENT_PHASE.md`](../CURRENT_PHASE.md)
2. [`../VALIDATION.md`](../VALIDATION.md)
3. [`TECHNICAL.md`](TECHNICAL.md)
4. [`../DECISIONS.md`](../DECISIONS.md)
