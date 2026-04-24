# Contributing

The repository remote is:

```text
https://github.com/ZSturman/Train-of-Thought-Agent.git
```

The project files currently use the public title "Tree-of-Thought Location Agent," while the repository URL uses "Train-of-Thought-Agent." TODO: confirm the preferred public name before broader publication.

## Local Workflow

1. Read [`../CURRENT_PHASE.md`](../CURRENT_PHASE.md) to understand the accepted current phase and the next target.
2. Make a focused change.
3. Run the full test suite:

```bash
python3 -B -m unittest discover -s tests -v
```

4. Update docs when behavior, commands, schema, media fixtures, or validation expectations change.
5. Keep runtime behavior grounded in explicit user input or direct sensor input.

## Documentation Expectations

This project is phase-driven. Code changes often need a matching update in one or more of these files:

| File | Update when |
| --- | --- |
| `CURRENT_PHASE.md` | The active phase behavior, commands, schema, or validation checklist changes. |
| `VALIDATION.md` | A phase is accepted, retested, or known validation state changes. |
| `CHANGELOG.md` | A meaningful implementation change lands. |
| `DECISIONS.md` | A design choice creates a constraint future contributors should understand. |
| `PROJECT_ROADMAP.md` | The phase plan changes. |
| `MEDIA_PLAN.md` | Media requirements or scenario ladder changes. |
| `media/catalog.json` | A committed media asset is added, removed, or repurposed. |

## Media Fixture Rules

Committed media should stay small, deterministic, and registered.

- Put fixture files under `media/core_images/` unless a later phase defines a new media pack.
- Add every committed asset to `media/catalog.json`.
- Add or update a scenario file in `media/scenarios/` when a phase depends on that asset.
- Record source kind and license for every media asset.
- Keep optional screenshots, GIFs, and videos under `docs/assets/` when they are for documentation rather than tests.

## Code Style Notes

- Prefer the existing standard-library style.
- Keep changes close to the phase goal.
- Preserve schema migrations for older runtime files.
- Do not store assistant-generated claims as persisted truth.
- Keep tests focused on behavior, migration, persistence, and validation invariants.

## Pull Requests

There is no detailed pull request template in the repository at this time. A useful PR should include:

- What changed.
- Why it changed.
- How it was tested.
- Any docs, media, or validation files updated.
- Any TODOs or limitations that remain.
