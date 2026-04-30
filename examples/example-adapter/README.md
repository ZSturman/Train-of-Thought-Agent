# example-adapter

A minimal external sensor adapter for `location_agent`. Demonstrates registering a custom modality via the `tot.adapters` entry-point group.

This package is **not installed in CI**. It is a reference layout you can copy when building your own adapter.

## Layout

```
example-adapter/
├── pyproject.toml
├── README.md
└── example_adapter/
    └── __init__.py
```

## Install (editable, for local experiments)

```sh
pip install -e ./examples/example-adapter
```

After installing in the same environment as `location_agent`, the `Agent` facade will pick up the new modality automatically:

```python
from location_agent import Agent
agent = Agent()
print(agent.adapters)  # {'image': ..., 'echo': <example_adapter.EchoAdapter>}
```
