"""Location-first learning agent — public SDK surface.

This module re-exports the stable public API. Names listed in ``__all__``
are covered by SemVer guarantees per ``docs/api.md``. Anything imported
from ``location_agent._internal`` or from a private submodule is **not**
part of the supported surface.

Quickstart::

    from location_agent import Agent

    agent = Agent()
    agent.learn_scalar(0.25, "kitchen")
    result = agent.recognize_scalar(0.253)
    print(result.label, result.confidence)
"""

from location_agent.agent import Agent, LearnResult, RecognitionResult
from location_agent.logging import EventLogger
from location_agent.memory import LabelConflictError, LabelLookupError, MemoryStore
from location_agent.models import (
    ImageAdapter,
    LabelNameError,
    ObservationBundle,
    ObservationError,
    RegionDescriptor,
    SensorAdapter,
    SensorObservationError,
)
from location_agent.plugins import load_adapters
from location_agent.session import SessionController
from location_agent.storage import MemoryStorage

# Alias: the legacy ``MemoryStore`` class is the local-JSON implementation.
LocalJSONStore = MemoryStore

__all__ = [
    "Agent",
    "EventLogger",
    "ImageAdapter",
    "LabelConflictError",
    "LabelLookupError",
    "LabelNameError",
    "LearnResult",
    "LocalJSONStore",
    "MemoryStorage",
    "MemoryStore",
    "ObservationBundle",
    "ObservationError",
    "RecognitionResult",
    "RegionDescriptor",
    "SensorAdapter",
    "SensorObservationError",
    "SessionController",
    "__version__",
    "load_adapters",
]
__version__ = "0.7.0rc1"
