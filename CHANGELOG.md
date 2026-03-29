# Changelog

## 2026-03-28

- Implemented Phase 2: Noisy Scalar Matching and Confidence Calibration.
- Added distance-based confidence model with linear decay within configurable
  tolerance (default 0.05), replacing binary exact-match confidence from Phase 1.
- Lowered guess threshold from 1.0 to 0.6, enabling confident noisy matches.
- Added `find_nearest()` nearest-neighbor lookup across all stored observations.
- Added uncertain-guess path: when confidence is positive but below threshold,
  the agent shows its best guess with uncertainty and asks for confirmation.
- Added near-collision guard: warns user when learning a new observation within
  tolerance of an existing one, preventing accidental label conflicts.
- Added transparent schema v1 → v2 migration on load (policy-only, no data changes).
- Added `tests/test_confidence.py` with 16 tests for distance functions, confidence
  calibration, find_nearest, and near-collision detection.
- Added 5 new session tests for noisy matching, uncertain guesses, far-observation
  unknown path, collision guard confirmation, and collision guard skip.
- Added noisy-query stress test: 100 learned observations with ±0.001 to ±0.06
  noisy queries verifying correct classification rates.
- Full suite: 30 tests passing (up from 8 in Phase 1).

## 2026-03-26

- Bootstrapped continuity artifacts for the long-horizon project, including roadmap, project state, current phase detail, decisions, validation template, and TODO tracking.
- Implemented Phase 1 with a stdlib-only Python package, persistent JSON memory, append-only JSONL event logging, interactive CLI loop, and regression coverage.
- Validated Phase 1 with 6 passing automated tests, a 1000-observation stress run, and a manual CLI smoke sequence using the public entrypoint.
