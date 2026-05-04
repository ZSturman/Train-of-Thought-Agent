"""Firestore-backed MemoryStorage (Release Phase R3).

Requires ``google-cloud-firestore``::

    pip install 'tot-agent[firestore]'

Data is stored as a single Firestore document per tenant at::

    tenants/{tenant_id}/memory/state

The document contains the same JSON structure as the local
``MemoryStore`` file, so schema migrations run automatically on load.
Per-tenant isolation is enforced by ``tenant_id``.

A process-local temp file satisfies ``MemoryStore``'s file bookkeeping;
it is deleted on garbage collection. For multi-process deployments (e.g.
Cloud Run with concurrency > 1) Firestore is the source of truth — the
last writer wins, which is acceptable at R3 traffic levels.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from location_agent.memory import MemoryStore

_TENANT_RE = re.compile(r"^[a-zA-Z0-9_\-]{1,128}$")
_FS_COLLECTION = "tenants"
_FS_MEMORY_DOC = "state"


class FirestoreStore(MemoryStore):
    """Firestore-backed :class:`~location_agent.storage.MemoryStorage`.

    Inherits all business logic from :class:`~location_agent.memory.MemoryStore`.
    Only the persistence layer changes: mutations are committed to Firestore
    instead of a local JSON file.

    Parameters
    ----------
    tenant_id:
        Namespace key for this tenant.  Must match ``[a-zA-Z0-9_-]{1,128}``.
    project_id:
        GCP project ID. Defaults to Application Default Credentials.
    credentials:
        Explicit ``google.auth`` credentials. Defaults to ADC.
    database:
        Firestore database ID. Defaults to ``"(default)"``.
    _client:
        Inject a pre-built Firestore client (or compatible mock). When
        supplied, ``project_id``, ``credentials``, and ``database`` are
        ignored and the ``google-cloud-firestore`` package need not be
        installed.  Intended for unit tests only.
    """

    def __init__(
        self,
        tenant_id: str,
        *,
        project_id: str | None = None,
        credentials: object | None = None,
        database: str | None = None,
        _client: object | None = None,
    ) -> None:
        if not _TENANT_RE.match(tenant_id):
            raise ValueError(
                "tenant_id must be 1–128 characters matching [a-zA-Z0-9_-], "
                f"got: {tenant_id!r}"
            )
        self._tenant_id = tenant_id

        # _db and _doc_ref are typed Any because google-cloud-firestore is an
        # optional dependency; mypy cannot resolve the stubs when it is absent.
        self._db: Any
        self._doc_ref: Any

        if _client is not None:
            self._db = _client
        else:
            try:
                from google.cloud import firestore as _fs  # type: ignore[import-not-found]
            except ImportError as exc:
                raise ImportError(
                    "google-cloud-firestore is required for FirestoreStore. "
                    "Install with: pip install 'tot-agent[firestore]'"
                ) from exc

            fs_kwargs: dict[str, Any] = {}
            if project_id is not None:
                fs_kwargs["project"] = project_id
            if credentials is not None:
                fs_kwargs["credentials"] = credentials
            if database is not None:
                fs_kwargs["database"] = database
            self._db = _fs.Client(**fs_kwargs)

        self._doc_ref = (
            self._db.collection(_FS_COLLECTION)
            .document(tenant_id)
            .collection("memory")
            .document(_FS_MEMORY_DOC)
        )

        # Temp file: MemoryStore needs a writable path for internal bookkeeping.
        # We seed it from Firestore so _load_or_initialize() reads the correct data.
        fd, tmp_str = tempfile.mkstemp(suffix=".json", prefix=f"tot-{tenant_id[:16]}-")
        os.close(fd)
        self._tmp_path = Path(tmp_str)

        snap = self._doc_ref.get()
        if snap.exists:
            payload = snap.to_dict()
            if payload:
                self._tmp_path.write_text(json.dumps(payload), encoding="utf-8")

        # super().__init__ calls _load_or_initialize() (reads temp file, runs
        # migrations) then may call _write_payload() (overridden below, which
        # syncs the migrated state back to Firestore).
        super().__init__(self._tmp_path)

    @property
    def tenant_id(self) -> str:
        return self._tenant_id

    def _write_payload(self, payload: dict[str, Any]) -> None:
        """Write to Firestore first, then keep the temp file in sync."""
        self._doc_ref.set(payload)
        super()._write_payload(payload)

    def __del__(self) -> None:
        try:
            if hasattr(self, "_tmp_path"):
                self._tmp_path.unlink(missing_ok=True)
        except Exception:  # noqa: BLE001
            pass

