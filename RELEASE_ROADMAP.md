# Release Roadmap

This file is the master plan for the **Release Track**. It runs in parallel with the existing 28-phase research roadmap in [`PROJECT_ROADMAP.md`](PROJECT_ROADMAP.md). v1.0 ships when **Research Phase 10 is accepted AND Release Phases R1–R12 are completed**. Research Phases 11–28 ship as post-1.0 minor releases.

For the rationale and full task breakdown, see the canonical plan in `/memories/session/plan.md`. The summary tables below are kept here for in-repo reference.

## Goal

Take the project from a hand-run research scaffold to a free, open-source product with three public surfaces:

1. **CLI** distributed via PyPI (`pip install tot-agent`, `pipx install tot-agent`).
2. **Web app** (Next.js + Firebase Auth/Firestore) at a hosted domain.
3. **HTTP API** (FastAPI on Cloud Run) backing the web app and reachable to third-party clients.

## Locked Decisions

- License: Apache-2.0
- PyPI name (target): `tot-agent`
- Python floor: 3.10
- Web stack: Next.js 14 (fallback Vite+React if integration friction)
- Hosted persistence: Firestore, web only. CLI/SDK stay local-first.
- Auth: Firebase Auth, anonymous mode permitted for the public demo.
- Cost target: ~$0/mo at low traffic, hard cap ~$5–10/mo at expected baseline.
- Article launch is independent of v1.0.

## Phase Index

| # | Phase | Status |
|---|---|---|
| R1 | Productization Foundation | Completed 2026-04-29 |
| R2 | Core SDK Extraction & Public API | In progress |
| R3 | HTTP API Service (FastAPI on Cloud Run) | Pending |
| R4 | Web App (Next.js + Firebase) | Pending |
| R5 | UX, Onboarding & Accessibility | Pending |
| R6 | Real Sensor Integration | Pending |
| R7 | Reliability, Security & Data | Pending |
| R8 | Observability, Telemetry & Feedback | Pending |
| R9 | Documentation, Examples & Public Demo | Pending (continuous from R1) |
| R10 | Performance, Scale & Cost | Pending |
| R11 | Beta & Release Hardening (gates on Research Phase 10) | Pending |
| R12 | Public v1.0 Launch | Pending |
| R13 | Post-launch & Steady-State | Pending |

## Critical Path

```
R1 → R2 → R3 → R4 ────────┐
              │   │       │
              │   ├── R5 ─┤
              │   └── R6 ─┤
              ├── R7 ─────┼── R11 ── R12 ── R13
              └── R8 ─────┤
            R9 (continuous from R1)
                  R10 ────┘
       Research 9 → 10 ───┘   (gates R12)
```

## Per-Phase Details

The full task list, dependencies, acceptance criteria, and risks for every release phase live in `/memories/session/plan.md`. When a phase becomes active, its checklist is copied into [`TODO.md`](TODO.md) and into the matching `CURRENT_RELEASE_PHASE.md` block.
