"""Pydantic request/response models for the REST routes."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models import Actor, SessionStatus


class CreateSessionRequest(BaseModel):
    role: str = Field(..., min_length=1, max_length=120)


class SessionResponse(BaseModel):
    id: str
    role: str
    status: SessionStatus
    scenario: dict
    created_at: datetime
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None


class EventResponse(BaseModel):
    id: int
    session_id: str
    ts_ms: int
    ts_abs: datetime
    actor: Actor
    type: str
    payload: dict


class ArtifactSnapshotRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., max_length=200_000)
    # Origin of the snapshot — debounced typing vs. an explicit save. Evaluators
    # can use this to distinguish ambient state from intentional checkpoints.
    trigger: str = Field("debounce", pattern="^(debounce|send|manual)$")


class ArtifactSnapshotResponse(BaseModel):
    ts_ms: int
    filename: str
    bytes: int


class AssistantQueryRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=10_000)


class AssistantQueryResponse(BaseModel):
    response: str
    query_ts_ms: int
    response_ts_ms: int
