"""SQLModel tables — v3.0.

v3 changes vs v2:
  - Session.format (A: multi-agent simulation; B: solo technical assessment)
  - Session.integrity_tier (standard | enhanced)
  - Session.accessibility (JSON: mode + extended_time multiplier + reduced_motion + high_contrast + dyslexia_font)
  - Session.session_minutes (band 30-90, default 60)
  - Session.is_practice (skips persistence into recruiter views)
  - Scorecard now stores 0–10 score, model-reported confidence ±, qualitative
    band, evaluator agreement, integrity context block, and an appeal stub.
  - Actor enum extends to PEER (Format A persona "peer", rebrand of teammate).

The same Day One spine applies to both formats. Format B simply skips the
cast/AI-assistant/twist event types and uses the Format B rubric.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class SessionFormat(str, Enum):
    """The two v3 formats. Architecture primitive — every session is one."""

    A = "A"  # Multi-Agent Work Simulation (cast + twist + AI assistant)
    B = "B"  # Solo Technical Assessment (code-only, no cast, no AI in-surface)


class IntegrityTier(str, Enum):
    """§6 — Standard ships by default; Enhanced opt-in for regulated roles."""

    STANDARD = "standard"
    ENHANCED = "enhanced"


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
    # Kept for back-compat with v2 event logs ("teammate"); §7 renames to "peer".
    TEAMMATE = "teammate"
    PEER = "peer"
    AI_ASSISTANT = "ai_assistant"
    SYSTEM = "system"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _default_accessibility() -> dict:
    return {
        "mode_enabled": False,
        "extended_time_multiplier": 1.0,  # 1.0, 1.5, or 2.0
        "reduced_motion": False,
        "high_contrast": False,
        "dyslexia_font": False,
        "screen_reader_optimized": False,
    }


class Session(SQLModel, table=True):
    """A single candidate run. One scenario or task set, many events, one scorecard."""

    id: str = Field(primary_key=True)
    role: str
    format: SessionFormat = Field(default=SessionFormat.A)
    integrity_tier: IntegrityTier = Field(default=IntegrityTier.STANDARD)
    is_practice: bool = Field(default=False)
    session_minutes: int = Field(default=60)  # band 30-90
    # Scenario (Format A) OR task set (Format B). Always a dict; shape differs.
    scenario_json: dict = Field(default_factory=dict, sa_column=Column(JSON))
    accessibility: dict = Field(default_factory=_default_accessibility, sa_column=Column(JSON))
    # Candidate identity (display only — not used in scoring). For demo: free-form.
    candidate_label: Optional[str] = None
    status: SessionStatus = Field(default=SessionStatus.CREATED)
    created_at: datetime = Field(default_factory=_utc_now)
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None


class Event(SQLModel, table=True):
    """Telemetry event — the richer this log, the better the evaluation."""

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="session.id", index=True)
    ts_ms: int  # ms since session.started_at; 0 if not yet started
    ts_abs: datetime = Field(default_factory=_utc_now)
    actor: Actor
    type: str
    payload: dict = Field(default_factory=dict, sa_column=Column(JSON))


class Scorecard(SQLModel, table=True):
    """One row per rubric axis with v3 fields.

    score_0_10 is the primary numerical signal. confidence_pm is the ±
    around the point estimate. band is the qualitative bucket. agreement
    is the ensemble-agreement indicator (model self-reported in single-pass
    mode; computed across ensemble samples in n>1 mode).
    """

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="session.id", index=True)
    axis: str
    # v3 0–10 scale (replaces v2's 1–5). Stored as float to preserve ensemble averages.
    score_0_10: float
    confidence_pm: float = Field(default=0.0)  # ± half-width of confidence interval
    band: str = Field(default="Mixed")  # Strong | Solid | Mixed | Limited | Insufficient signal
    agreement: str = Field(default="medium")  # high | medium | low | divergent
    summary: str
    evidence: list = Field(default_factory=list, sa_column=Column(JSON))
    flagged: bool = Field(default=False)
    created_at: datetime = Field(default_factory=_utc_now)


class Appeal(SQLModel, table=True):
    """Candidate-initiated human-review request. v3 §11.5."""

    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="session.id", index=True)
    reason: str
    status: str = Field(default="pending")  # pending | acknowledged | resolved
    created_at: datetime = Field(default_factory=_utc_now)
