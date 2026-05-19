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
