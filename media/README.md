# Media Fixtures

This directory holds repo-local sensor fixtures and ordered scenario manifests for the Tree-of-Thought Location Agent.

## Purpose

- Keep Phase 4 and later sensor work deterministic and lightweight.
- Give every phase an explicit media pack and validation scenario before code depends on richer sensing.
- Provide a clean ladder from committed fixtures to annotated region corpora, frame and replay traces, multimodal context replays, and long-horizon audit bundles.

## Layout

- `catalog.json` — authoritative asset metadata
- `core_images/` — committed image-first fixtures used by the current sensor preview
- `scenarios/` — ordered validation bundles keyed by `scenario_id`

Future phases may add annotation sidecars or replay bundles, but they should still map back to assets registered in `catalog.json` and to the common `ObservationBundle` contract described in `MEDIA_PLAN.md`.

## Naming

- Use `phaseNN_` prefixes for assets first introduced in a phase.
- Prefer semantic scene names such as `phase04_break_room_scene.png`.
- Keep `asset_id` values stable even if a file is regenerated later.
- Use scenario ids and notes to say whether an asset is for exact-file preview, annotated region attention, cue composition, frame or replay validation, pose or motion context, or audit and repair workflows.

## Provenance

- `source_kind` must describe where the asset came from, such as `generated-local`, `captured-local`, or `downloaded-reference`.
- `license` must be recorded for every asset, even for locally generated fixtures.
- Media files are inputs only. Persisted memory still records truth sources only as `user` or `sensor`.

## Size Limits

- Keep committed fixtures small enough for fast checkout and test runs.
- Default image fixtures should remain below 100 KB each unless there is a strong reason to exceed that budget.
- Prefer a small deterministic pack over a large realistic corpus until a phase explicitly requires more coverage.

## Sourcing Rules

- Repo-local fixtures are the default for tests and docs.
- Optional internet pulls or generated enrichments must stay outside required CI paths.
- If a future phase needs richer captures, add them behind a new scenario manifest and update `MEDIA_PLAN.md` before relying on them.
