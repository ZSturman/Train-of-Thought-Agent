# Current Release Phase

- Status: in_progress
- Phase: R3
- Title: HTTP API & Hosted Storage
- Started: 2026-05-03
- Previous phase: R2 — Core SDK Extraction & Public API (completed 2026-04-30; TestPyPI smoke test verified 2026-05-03)
- Next phase: R4 — Web App (Next.js + Firebase)

---

## What R3 Will Deliver

R3 exposes the SDK over HTTP (FastAPI) and adds a hosted memory backend (Firestore) so the upcoming web app (R4) can run against a remote instance. It also introduces an async surface on `Agent` for API workers, deployment artifacts, and the production PyPI publish of `tot-agent 0.7.0`.

## R3 Checklist

See [`TODO.md`](TODO.md) for the authoritative per-task status.

- [ ] Async `Agent` wrapper (`AsyncAgent`) for FastAPI workers
- [ ] Concrete `FirestoreStore` implementing `MemoryStorage`
- [ ] FastAPI REST surface (`POST /learn`, `/recognize`, `/confirm`, `/correct`; `GET /inspect`; `POST /reset`)
- [ ] OpenAPI spec checked into the repo (`docs/openapi.json`)
- [ ] Auth + multi-tenant scoping (API key for R3)
- [ ] `tests/test_http_api.py` end-to-end against in-memory store
- [ ] `tests/test_firestore_store.py` against the Firestore emulator
- [ ] Dockerfile + Cloud Run / Fly.io manifest
- [ ] Production PyPI publish of `tot-agent 0.7.0`

## Acceptance Criteria

- `curl` against the running service drives teach → recognize → inspect.
- Firestore store passes the same Protocol contract tests as `LocalJSONStore`.
- Coverage ≥ 80%; mypy clean; CI matrix green.

## How to Verify R3 Locally

```bash
pip install -e ".[dev,api,firestore]"
uvicorn location_agent.api:app --reload
curl -s http://localhost:8000/docs   # OpenAPI UI
curl -s -X POST http://localhost:8000/learn -d '{"value": 0.25, "label": "kitchen"}' -H 'Content-Type: application/json'
curl -s -X POST http://localhost:8000/recognize -d '{"value": 0.253}' -H 'Content-Type: application/json'
curl -s http://localhost:8000/inspect
pytest --cov=location_agent --cov-fail-under=80
```

## How the Release Track Is Tracked

- [`TODO.md`](TODO.md) holds **only** the active phase's checklist (currently R3's).
- On phase completion, the previous phase's checklist is copied into [`CHANGELOG.md`](CHANGELOG.md) under a dated heading and replaced in `TODO.md` with the next phase's items.
- [`PROJECT_STATE.json`](PROJECT_STATE.json) carries machine-readable status for both research and release tracks.
- [`PROJECT_ROADMAP.md`](PROJECT_ROADMAP.md) holds the long-range research-track phases (1–28). The release-track phases (R1–R13) are documented in [`RELEASE_ROADMAP.md`](RELEASE_ROADMAP.md).
