"""HTTP API for the location-agent SDK (Release Phase R3).

Run with::

    uvicorn location_agent.api:app --host 0.0.0.0 --port 8080

Environment variables
---------------------
TOT_API_KEY
    Required. API key that clients supply via the ``X-API-Key`` request header.
TOT_STORAGE_BACKEND
    ``local`` (default) or ``firestore``.
TOT_RUNTIME_DIR
    Path for local JSON storage. Defaults to ``./runtime``.
TOT_TENANT_ID
    Firestore tenant ID. Defaults to ``default``.
TOT_GCP_PROJECT
    GCP project ID for Firestore (optional; falls back to Application Default
    Credentials).
"""

from __future__ import annotations

import os
import secrets
import threading
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

from location_agent.agent import Agent
from location_agent.memory import LabelConflictError
from location_agent.models import LabelNameError

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Train-of-Thought Agent",
    version="0.7.0",
    description=(
        "HTTP API for the Train-of-Thought Location Agent SDK. "
        "All endpoints require an ``X-API-Key`` header."
    ),
    openapi_tags=[
        {"name": "learning", "description": "Teach the agent new locations."},
        {"name": "recognition", "description": "Recognize observed locations."},
        {"name": "inspection", "description": "Inspect and manage learned state."},
    ],
)

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

_API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=True)


def _require_api_key(key: str = Security(_API_KEY_HEADER)) -> str:
    expected = os.environ.get("TOT_API_KEY", "")
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TOT_API_KEY is not configured on this server.",
        )
    # Constant-time comparison prevents timing-based key enumeration.
    if not secrets.compare_digest(key.encode(), expected.encode()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
        )
    return key


# ---------------------------------------------------------------------------
# Agent factory
# ---------------------------------------------------------------------------

_agent_singleton: Agent | None = None
_agent_lock: threading.Lock = threading.Lock()


def _create_agent() -> Agent:
    backend = os.environ.get("TOT_STORAGE_BACKEND", "local")
    if backend == "firestore":
        from location_agent._internal.firestore_store import (  # noqa: PLC0415
            FirestoreStore,
        )

        tenant_id = os.environ.get("TOT_TENANT_ID", "default")
        project_id = os.environ.get("TOT_GCP_PROJECT") or None
        store = FirestoreStore(tenant_id=tenant_id, project_id=project_id)
        return Agent(store=store)
    runtime_dir = os.environ.get("TOT_RUNTIME_DIR", "./runtime")
    return Agent(runtime_dir=runtime_dir)


def get_agent() -> Agent:
    """Return the process-wide Agent singleton.

    Override via ``app.dependency_overrides[get_agent]`` in tests to inject a
    fresh in-memory agent per test.
    """
    global _agent_singleton
    with _agent_lock:
        if _agent_singleton is None:
            _agent_singleton = _create_agent()
    return _agent_singleton


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class LearnScalarRequest(BaseModel):
    value: float = Field(..., ge=0.0, le=1.0, description="Scalar observation in [0.0, 1.0].")
    label: str = Field(..., min_length=1, max_length=256, description="Location label.")


class RecognizeScalarRequest(BaseModel):
    value: float = Field(..., ge=0.0, le=1.0, description="Scalar observation to recognize.")


class ConfirmRequest(BaseModel):
    value: float = Field(..., ge=0.0, le=1.0)
    location_id: str = Field(..., min_length=1, max_length=128)


class CorrectRequest(BaseModel):
    value: float = Field(..., ge=0.0, le=1.0)
    location_id: str = Field(..., min_length=1, max_length=128)
    new_label: str = Field(..., min_length=1, max_length=256)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.post("/learn", tags=["learning"], summary="Learn a scalar observation.")
def learn(
    request: LearnScalarRequest,
    agent: Agent = Depends(get_agent),
    _key: str = Security(_require_api_key),
) -> dict[str, Any]:
    try:
        result = agent.learn_scalar(request.value, request.label)
    except LabelNameError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except LabelConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return {
        "location_id": result.location_id,
        "label": result.label,
        "snapshot": result.snapshot,
    }


@app.post("/recognize", tags=["recognition"], summary="Recognize a scalar observation.")
def recognize(
    request: RecognizeScalarRequest,
    agent: Agent = Depends(get_agent),
    _key: str = Security(_require_api_key),
) -> dict[str, Any]:
    result = agent.recognize_scalar(request.value)
    return {
        "is_known": result.is_known,
        "label": result.label,
        "confidence": result.confidence,
        "location_id": result.location_id,
    }


@app.post("/confirm", tags=["recognition"], summary="Confirm a recognition was correct.")
def confirm(
    request: ConfirmRequest,
    agent: Agent = Depends(get_agent),
    _key: str = Security(_require_api_key),
) -> dict[str, Any]:
    try:
        return agent.confirm_scalar(request.value, request.location_id)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@app.post("/correct", tags=["recognition"], summary="Correct a wrong recognition.")
def correct(
    request: CorrectRequest,
    agent: Agent = Depends(get_agent),
    _key: str = Security(_require_api_key),
) -> dict[str, Any]:
    try:
        return agent.correct_scalar(request.value, request.location_id, request.new_label)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (LabelNameError, LabelConflictError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc


@app.get("/inspect", tags=["inspection"], summary="Inspect the full learned state.")
def inspect(
    agent: Agent = Depends(get_agent),
    _key: str = Security(_require_api_key),
) -> dict[str, Any]:
    return agent.inspect()


@app.post("/reset", tags=["inspection"], summary="Clear all learned location memory.")
def reset(
    agent: Agent = Depends(get_agent),
    _key: str = Security(_require_api_key),
) -> dict[str, Any]:
    cleared = agent.reset()
    return {"cleared": cleared}
