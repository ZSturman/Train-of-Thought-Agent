"""Sensor adapter plugin discovery via setuptools entry points.

External packages register `SensorAdapter` implementations under the
``tot.adapters`` entry-point group::

    # In a third-party package's pyproject.toml:
    [project.entry-points."tot.adapters"]
    audio = "my_pkg.audio:AudioAdapter"

`load_adapters()` returns a mapping of ``modality`` (or entry-point name
fallback) to a constructed `SensorAdapter` instance, ready to plug into
the `Agent` facade.

Threat model: any installed Python package can register an adapter under
this group. Discovery does **not** sandbox or sign adapter code. Trust
boundary is the Python environment — install adapters from sources you
trust.
"""

from __future__ import annotations

import logging
from importlib.metadata import EntryPoint, entry_points

from location_agent.models import SensorAdapter

ADAPTER_GROUP = "tot.adapters"

logger = logging.getLogger(__name__)


def _select_entry_points(group: str) -> tuple[EntryPoint, ...]:
    """Return all entry points registered under *group*.

    Wraps ``importlib.metadata.entry_points`` to support both the
    pre-3.10 dict-style API and the post-3.10 ``select`` API.
    """
    eps = entry_points()
    selector = getattr(eps, "select", None)
    if selector is not None:
        return tuple(selector(group=group))
    return tuple(eps.get(group, []))


def load_adapters() -> dict[str, SensorAdapter]:
    """Discover and instantiate all registered sensor adapters.

    Returns a dict keyed by adapter ``modality`` (falling back to the
    entry-point name on collision). Adapters that fail to load or do not
    inherit from `SensorAdapter` are skipped with a warning.
    """
    discovered: dict[str, SensorAdapter] = {}
    for ep in _select_entry_points(ADAPTER_GROUP):
        try:
            cls = ep.load()
        except Exception:
            logger.warning("failed to load adapter entry point %r", ep.name, exc_info=True)
            continue
        try:
            instance = cls()
        except Exception:
            logger.warning("failed to instantiate adapter %r", ep.name, exc_info=True)
            continue
        if not isinstance(instance, SensorAdapter):
            logger.warning(
                "entry point %r does not produce a SensorAdapter instance; got %r",
                ep.name,
                type(instance).__name__,
            )
            continue
        key = instance.modality or ep.name
        if key in discovered:
            key = ep.name
        discovered[key] = instance
    return discovered
