"""Pydantic request/response models — v3.0.

Notable v3 additions:
  - CreateSessionRequest accepts `format`, `is_practice`, `session_minutes`,
    `integrity_tier`, `accessibility`, `candidate_label`.
  - ScorecardAxisResponse carries score_0_10 + confidence_pm + band +
    agreement + flagged.
  - IntegrityContext is its own typed payload, surfaced on the scorecard
    separate from rubric scores (§6.4 — descriptive, never adjudicatory).
  - Appeal request/response per §11.5.
  - RecruiterSessionRow for the dashboard listing.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.models import Actor, IntegrityTier, SessionFormat, SessionStatus


# ----- session create / read -----


class AccessibilityPrefs(BaseModel):
    mode_enabled: bool = False
    extended_time_multiplier: float = Field(default=1.0, ge=1.0, le=2.0)
    reduced_motion: bool = False
    high_contrast: bool = False
    dyslexia_font: bool = False
    screen_reader_optimized: bool = False


class CreateSessionRequest(BaseModel):
    role: str = Field(..., min_length=1, max_length=120)
    format: SessionFormat = SessionFormat.A
    session_minutes: int = Field(default=60, ge=30, le=90)
    integrity_tier: IntegrityTier = IntegrityTier.STANDARD
    accessibility: AccessibilityPrefs = Field(default_factory=AccessibilityPrefs)
    is_practice: bool = False
    candidate_label: Optional[str] = Field(default=None, max_length=120)


class SessionResponse(BaseModel):
    id: str
    role: str
    format: SessionFormat
    integrity_tier: IntegrityTier
    is_practice: bool
    session_minutes: int
    status: SessionStatus
    scenario: dict
    accessibility: AccessibilityPrefs
    candidate_label: Optional[str] = None
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


# ----- work-surface telemetry -----


class ArtifactSnapshotRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., max_length=200_000)
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


# ----- integrity events (§6.2) -----


class TabFocusEvent(BaseModel):
    """Tab-switch logging — context, never scored. §6.2 Standard tier default."""

    kind: Literal["lost", "regained"]
    away_ms: Optional[int] = Field(default=None, ge=0)


class PasteAttributionRequest(BaseModel):
    """Paste attribution — surfaces what was pasted from where. §6.2."""

    target: Literal["work_surface", "chat", "assistant"]
    bytes: int = Field(..., ge=0)
    source: Literal["external", "internal", "unknown"] = "external"
    preview: str = Field("", max_length=400)  # short preview, never the whole paste


class IntegrityEventResponse(BaseModel):
    ts_ms: int
    type: str


# ----- v3 scorecard -----


class ScorecardEvidenceResponse(BaseModel):
    event_id: int
    ts_ms: int
    quote: str
    reasoning: str


class ScorecardAxisResponse(BaseModel):
    """Per-axis result. Reported per §4.4."""

    axis: str
    score_0_10: float
    confidence_pm: float
    band: str  # Strong | Solid | Mixed | Limited | Insufficient signal
    agreement: str  # high | medium | low | divergent
    summary: str
    evidence: list[ScorecardEvidenceResponse]
    flagged: bool = False


class IntegrityContextResponse(BaseModel):
    """Descriptive integrity facts surfaced separately from rubric. §6.4."""

    tab_focus_lost_count: int
    tab_focus_total_away_ms: int
    paste_event_count: int
    paste_external_bytes: int
    ai_assistant_turn_count: int  # 0 for Format B by design
    cast_message_count: int  # 0 for Format B by design
    notes: list[str]  # plain-language commentary (e.g., "No tab switches observed.")


SCORECARD_DISCLAIMER = (
    "Decision support for a human reviewer — not an automated verdict. "
    "Each axis is scored 0–10 with a confidence interval, qualitative band, "
    "and evaluator-agreement indicator. Every score cites timestamped moments "
    "from this session; review the evidence and use your own judgment."
)


class ScorecardResponse(BaseModel):
    session_id: str
    format: SessionFormat
    is_practice: bool
    disclaimer: str = SCORECARD_DISCLAIMER
    axes: list[ScorecardAxisResponse]
    integrity: IntegrityContextResponse


# ----- explanation surface (§11.4) -----


class AxisExplanation(BaseModel):
    axis: str
    plain_language: str
    what_we_measure: str
    what_we_dont_measure: str


class ExplanationResponse(BaseModel):
    session_id: str
    format: SessionFormat
    intro: str
    per_axis: list[AxisExplanation]
    rights: list[str]
    sub_processors: list[str]


# ----- appeal (§11.5) -----


class AppealRequest(BaseModel):
    reason: str = Field(..., min_length=8, max_length=2000)


class AppealResponse(BaseModel):
    id: int
    session_id: str
    status: str
    created_at: datetime


# ----- recruiter dashboard (§12.1) -----


class RecruiterSessionRow(BaseModel):
    id: str
    role: str
    format: SessionFormat
    status: SessionStatus
    candidate_label: Optional[str] = None
    is_practice: bool
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    axes_summary: list[dict]  # [{axis, score_0_10, band, flagged}]
