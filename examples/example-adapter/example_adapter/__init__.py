"""Reference sensor adapter for location_agent.

Echoes the raw input as a single primitive feature. Useful as a
template — replace `observe()` with real sensor processing.
"""

from __future__ import annotations

import hashlib

from location_agent import ObservationBundle, SensorAdapter
from location_agent.models import utc_now_iso


class EchoAdapter(SensorAdapter):
    """Trivial adapter that turns any string into a deterministic bundle."""

    @property
    def adapter_id(self) -> str:
        return "echo-adapter-v0"

    @property
    def modality(self) -> str:
        return "echo"

    def observe(self, raw_input: str) -> ObservationBundle:
        digest = hashlib.sha256(raw_input.encode("utf-8")).hexdigest()
        return ObservationBundle(
            bundle_id=f"echo-{digest[:12]}",
            timestamp=utc_now_iso(),
            adapter_id=self.adapter_id,
            modality=self.modality,
            primitive_features=(raw_input,),
            raw_refs=(f"sha256:{digest}",),
            provenance="sensor",
        )


__all__ = ["EchoAdapter"]
