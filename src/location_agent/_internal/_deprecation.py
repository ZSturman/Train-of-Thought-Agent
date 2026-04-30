"""Deprecation helper — emits ``DeprecationWarning`` for callers of legacy names."""

from __future__ import annotations

import warnings


def deprecated(name: str, replacement: str | None = None, removed_in: str | None = None) -> None:
    """Emit a ``DeprecationWarning`` for the named symbol.

    Parameters
    ----------
    name:
        Fully-qualified name of the deprecated symbol.
    replacement:
        Optional name of the replacement symbol callers should migrate to.
    removed_in:
        Optional target version at which the symbol will be removed.
    """
    parts = [f"{name} is deprecated"]
    if replacement is not None:
        parts.append(f"; use {replacement} instead")
    if removed_in is not None:
        parts.append(f"; will be removed in {removed_in}")
    warnings.warn("".join(parts), DeprecationWarning, stacklevel=3)
