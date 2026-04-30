# Sensor Adapter Plugins

`location_agent` discovers sensor adapters at runtime via Python's standard [entry points](https://packaging.python.org/en/latest/specifications/entry-points/) mechanism. This lets external packages add new modalities (audio, depth, IMU, etc.) without modifying the core SDK.

## Registering an adapter

In your package's `pyproject.toml`:

```toml
[project.entry-points."tot.adapters"]
audio = "my_audio_pkg.adapter:AudioAdapter"
```

The entry-point group is `tot.adapters`. The key (`audio` above) is used as a fallback modality identifier; the value is the import path to a class that subclasses `location_agent.SensorAdapter`.

## Adapter contract

Your adapter class must implement the `SensorAdapter` ABC:

```python
from location_agent import SensorAdapter, ObservationBundle

class AudioAdapter(SensorAdapter):
    @property
    def adapter_id(self) -> str:
        return "audio-adapter-v0"

    @property
    def modality(self) -> str:
        return "audio"

    def observe(self, raw_input: str) -> ObservationBundle:
        ...
```

`load_adapters()` (called automatically by `Agent`) will:

1. Enumerate all entry points under `tot.adapters`.
2. Import each target and instantiate it with no arguments.
3. Verify the instance is a `SensorAdapter`.
4. Key the result by `instance.modality` (falling back to the entry-point name on collision).

Adapters that fail import, fail instantiation, or are not `SensorAdapter` subclasses are skipped with a `WARNING` log on the `location_agent.plugins` logger.

## Threat model

> **Important**: any installed Python package can register an adapter under the `tot.adapters` group. `load_adapters()` does **not** sandbox, sign, or verify the adapter code in any way. Discovery runs adapter constructors at import time of your application.

The trust boundary is the Python environment. Mitigations:

- Pin your dependencies. Do not install adapter packages from untrusted sources.
- If you need to disable plugin discovery, pass an explicit `adapters=` dict to `Agent()`:

  ```python
  from location_agent import Agent, ImageAdapter
  agent = Agent(adapters={"image": ImageAdapter()})
  ```

  An empty dict (`adapters={}`) disables all sensor input.

- Audit installed entry points: `python -c "from importlib.metadata import entry_points; print(list(entry_points(group='tot.adapters')))"`.

We will revisit signing or sandboxing only if a concrete deployment story requires it. For research and local-CLI use the env-trust model is sufficient.

## Example

A minimal external adapter package layout is in [`examples/example-adapter/`](../examples/example-adapter/).
