"""SQLModel tables — Session, Event, Scorecard.

Schema mirrors §5 of the build plan. SQLite is the backing store; JSON columns
use SQLAlchemy's portable JSON type (TEXT under the hood on SQLite).
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class SessionStatus(str, Enum):
    CREATED = "created"
    BRIEFING = "briefing"
    ACTIVE = "active"
    WRAPPING = "wrapping"
    SCORING = "scoring"
    COMPLETE = "complete"


class Actor(str, Enum):
    CANDIDATE = "candidate"
    PM = "pm"
    REVIEWER = "reviewer"
    TEAMMATE = "teammate"
    AI_ASSISTANT = "ai_assistant"
    SYSTEM = "system"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Session(SQLModel, table=True):
    """A single candidate run. One scenario, many events, one scorecard."""

    id: str = Field(primary_key=True)
    role: str
    scenario_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    status: SessionStatus = Field(default=SessionStatus.CREATED)
    created_at: datetime = Field(default_factory=_utc_now)
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None


class Event(SQLModel, table=True):
    """Telemetry event — the richer this log, the better the evaluation."""

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="session.id", index=True)
    # ms since session.started_at; 0 if the session hasn't started yet.
    ts_ms: int
    ts_abs: datetime = Field(default_factory=_utc_now)
    actor: Actor
    type: str
    payload: dict = Field(default_factory=dict, sa_column=Column(JSON))


class Scorecard(SQLModel, table=True):
    """One row per rubric axis. Evidence is a JSON list of cited events."""

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="session.id", index=True)
    axis: str
    score: int  # 1–5
    summary: str
    evidence: list = Field(default_factory=list, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=_utc_now)
