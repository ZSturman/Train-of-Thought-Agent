# Current Release Phase

- Status: completed
- Phase: R2
- Title: Core SDK Extraction & Public API
- Validation result: accepted — 197 tests pass, mypy --strict clean, public surface frozen, JSON schemas published, plugin discovery wired
- Next phase: R3 — HTTP API & Hosted Storage

---

## What R2 Delivered

R2 promoted `location_agent` from "library you can import" to "SDK you can build a product on top of". The `Agent` facade is now the single recommended entry point; `MemoryStorage` is a runtime-checkable Protocol so backends can be swapped; sensor adapters are discovered via Python entry points; and the public surface is frozen behind a SemVer policy documented in `docs/api.md`.

See [`CHANGELOG.md`](CHANGELOG.md) for the full set of changes.

## How to Verify R2 Locally

```bash
# Set up
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Smoke
tot --version                           # tot-agent 0.7.0rc1
python -c "from location_agent import Agent; a = Agent(); a.learn_scalar(0.25, 'kitchen'); print(a.recognize_scalar(0.253))"

# Quality gates
ruff check .
ruff format --check .
mypy src/location_agent
pytest --cov=location_agent --cov-fail-under=80

# Build
python -m build
twine check dist/*
```

## Open Items Carried Forward (Track in R3)

- TestPyPI publish for `0.7.0rc1` is gated on a manual workflow run; trigger when ready to reserve the name.
- The async surface is deferred to R3 — `Agent` is sync-only today; an async wrapper will be added when the FastAPI service lands.
- `_internal/firestore_store.py` is a stub. R3's first deliverable is the concrete Firestore implementation behind the same `MemoryStorage` Protocol.

## How the Release Track Is Tracked

- [`TODO.md`](TODO.md) holds **only** the active phase's checklist (currently R3's).
- On phase completion, the previous phase's checklist is copied into [`CHANGELOG.md`](CHANGELOG.md) under a dated heading and replaced in `TODO.md` with the next phase's items.
- [`PROJECT_STATE.json`](PROJECT_STATE.json) carries machine-readable status for both research and release tracks.
- [`PROJECT_ROADMAP.md`](PROJECT_ROADMAP.md) holds the long-range research-track phases (1–28). The release-track phases (R1–R13) are documented in [`RELEASE_ROADMAP.md`](RELEASE_ROADMAP.md).
