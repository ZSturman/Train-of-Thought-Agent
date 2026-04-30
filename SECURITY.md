# Security Policy

## Supported Versions

Until v1.0.0, only the latest `0.x` minor release receives security fixes.

| Version  | Supported          |
| -------- | ------------------ |
| 0.x      | :white_check_mark: |
| < 0.5    | :x:                |

## Reporting a Vulnerability

Please **do not** open a public GitHub issue for suspected security
vulnerabilities. Instead:

1. Use GitHub's private vulnerability reporting:
   <https://github.com/ZSturman/Train-of-Thought-Agent/security/advisories/new>
2. Or email the maintainer directly via the address listed on the GitHub
   profile of [@ZSturman](https://github.com/ZSturman).

You can expect:

- An initial acknowledgement within 5 business days.
- A triage assessment (severity, scope, fix plan) within 14 days.
- A coordinated disclosure window before any public advisory.

## Scope

In scope:

- The `tot-agent` Python package and its CLI.
- The hosted HTTP API service (once deployed in Release Phase R3).
- The hosted web app (once deployed in Release Phase R4).

Out of scope (until explicitly added later):

- Third-party `SensorAdapter` plugins distributed by other authors.
- Local user runtime data (`runtime/` directory) — users are responsible for
  protecting this on their own machines.

## Versioning Promise

Once v1.0.0 ships, the project follows semantic versioning. Public surfaces
covered by the SemVer promise are documented in `docs/api.md` (added in
Release Phase R2).
