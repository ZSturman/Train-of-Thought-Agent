# Public API & SemVer Policy

This document defines the **stable public surface** of the `location_agent` package. Anything documented here is governed by [Semantic Versioning](https://semver.org/) starting with `0.7.0rc1`.

## Public surface

The following names — and only these — are guaranteed by SemVer:

```python
from location_agent import (
    Agent,
    LearnResult,
    RecognitionResult,
    MemoryStorage,
    MemoryStore,
    LocalJSONStore,
    EventLogger,
    SensorAdapter,
    ImageAdapter,
    ObservationBundle,
    RegionDescriptor,
    load_adapters,
    ObservationError,
    LabelNameError,
    SensorObservationError,
    LabelConflictError,
    LabelLookupError,
)
```

The exported names are the single source of truth in [`location_agent/__init__.py`](../src/location_agent/__init__.py) under `__all__`. The package's `__version__` is also part of the public API.

### What stability means

For these names, between minor versions we will not:

- Remove a public name.
- Remove a method, property, or constructor parameter.
- Add a required positional parameter.
- Tighten an input type or loosen a return type in a way that breaks existing callers.

We may:

- Add new names, methods, or keyword-only parameters with defaults.
- Add new fields to dataclasses with defaults.
- Improve performance, error messages, and internal behavior.

Breaking changes will only ship in major releases (1.0 → 2.0) with a migration note in `CHANGELOG.md`.

### Versions before 1.0

Pre-1.0 versions follow the convention that **minor** bumps may include breaking changes, but every break will be called out in `CHANGELOG.md`. Patch versions are always non-breaking.

## Internal surface

Anything imported from these locations is **not** part of the public API and may change in any release:

- `location_agent._internal.*` — explicit internal package.
- Any submodule attribute not re-exported from `location_agent.__init__`.
- Private attributes (leading underscore) on public classes.
- Module layout: do not import `location_agent.agent`, `location_agent.memory`, etc., directly. Use `from location_agent import ...`.

The `_internal/` package contains R3 work in progress (e.g. `FirestoreStore`) that is intentionally not yet stable.

## SessionController carve-out

`SessionController` is exported because the CLI in this repo depends on it, but it is the **interactive loop driver** and is *not* recommended for SDK consumers. Programmatic users should use `Agent`. We reserve the right to change `SessionController`'s constructor signature and method shape across minor versions; treat it as advisory.

## Storage Protocol

`MemoryStorage` is a `typing.Protocol` (runtime-checkable). To plug in an alternate backend (e.g. a hosted store):

```python
from location_agent import Agent, MemoryStorage

class MyStore:
    # implement the methods listed on MemoryStorage
    ...

agent = Agent(store=MyStore())
```

The Protocol's method list is the contract. Adding new methods to `MemoryStorage` in a minor release will only be done with default implementations or runtime fallbacks so existing user-defined stores keep working.

## Plugins

See [plugins.md](plugins.md) for the sensor-adapter plugin contract.
