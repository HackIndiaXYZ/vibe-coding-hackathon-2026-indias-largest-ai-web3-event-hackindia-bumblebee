"""FastAPI entrypoint — v3.0.

Routes:

  Lifecycle
    POST   /sessions                            (format-aware)
    GET    /sessions/{id}
    POST   /sessions/{id}/start
    POST   /sessions/{id}/end                   (runs evaluators)
    GET    /sessions/{id}/scorecard             (v3 scorecard + integrity)
    GET    /sessions/{id}/explanation           (right-to-explanation §11.4)
    GET    /sessions/{id}/events

  Work surface + AI
    POST   /sessions/{id}/artifact
    POST   /sessions/{id}/assistant             (Format A only — 409 on B)

  Integrity (§6.2 Standard tier — context, never scoring)
    POST   /sessions/{id}/integrity/tab-focus
    POST   /sessions/{id}/integrity/paste

  Candidate rights (§11)
    POST   /sessions/{id}/appeal                (human-review request)

  Recruiter (§12.1)
    GET    /recruiter/sessions                  (dashboard listing)

  WebSocket
    WS     /sessions/{id}/ws                    (Format A only)
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Awaitable, Callable
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session as DbSession, select

from app.agents.assistant import assistant_reply as _default_assistant_reply
from app.agents.evaluators import (
    AxisVerdict,
    ScoringError,
    band_for,
    evaluate_session as _default_evaluate_session,
)
from app.agents.scenario_engine import (
    Scenario,
    ScenarioGenerationError,
    generate_scenario,
)
from app.agents.task_engine import (
    TaskSet,
    TaskSetGenerationError,
    generate_task_set,
)
from app.config import settings
from app.db import engine, get_session, init_db
from app.models import (
    Actor,
    Appeal,
    Event,
    IntegrityTier,
    Scorecard,
    Session as SessionModel,
    SessionFormat,
    SessionStatus,
)
from app.orchestrator import CHANNELS, SessionOrchestrator, history_for_channel
from app.schemas import (
    AppealRequest,
    AppealResponse,
    ArtifactSnapshotRequest,
    ArtifactSnapshotResponse,
    AssistantQueryRequest,
    AssistantQueryResponse,
    AxisExplanation,
    CreateSessionRequest,
    EventResponse,
    ExplanationResponse,
    IntegrityContextResponse,
    PasteAttributionRequest,
    RecruiterSessionRow,
    ScorecardAxisResponse,
    ScorecardEvidenceResponse,
    ScorecardResponse,
    SessionResponse,
    TabFocusEvent,
)
from app.telemetry import get_events, log_event


AssistantReplyFn = Callable[..., Awaitable[str]]
EvaluateSessionFn = Callable[..., Awaitable[list[AxisVerdict]]]
ScenarioGenerator = Callable[[str], Awaitable[Scenario]]
TaskSetGenerator = Callable[..., Awaitable[TaskSet]]


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Day One", version="3.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----- dependency providers (overridable in tests) -----


def get_scenario_generator() -> ScenarioGenerator:
    return generate_scenario


def get_task_set_generator() -> TaskSetGenerator:
    return generate_task_set


def get_assistant_reply() -> AssistantReplyFn:
    return _default_assistant_reply


def get_session_evaluator() -> EvaluateSessionFn:
    return _default_evaluate_session


# ----- serializers -----


def _to_response(s: SessionModel) -> SessionResponse:
    return SessionResponse(
        id=s.id,
        role=s.role,
        format=s.format,
        integrity_tier=s.integrity_tier,
        is_practice=s.is_practice,
        session_minutes=s.session_minutes,
        status=s.status,
        scenario=s.scenario_json or {},
        accessibility=s.accessibility,
        candidate_label=s.candidate_label,
        created_at=s.created_at,
        started_at=s.started_at,
        ended_at=s.ended_at,
    )


# ============================================================================
# Health
# ============================================================================


@app.get("/health")
async def health() -> dict[str, str | int]:
    return {
        "status": "ok",
        "service": "day-one",
        "version": app.version,
        "evaluator_ensemble_n": settings.evaluator_ensemble_n,
    }


# ============================================================================
# Sessions
# ============================================================================


@app.post("/sessions", response_model=SessionResponse, status_code=201)
async def create_session(
    req: CreateSessionRequest,
    db: DbSession = Depends(get_session),
    scenario_gen: ScenarioGenerator = Depends(get_scenario_generator),
    task_gen: TaskSetGenerator = Depends(get_task_set_generator),
) -> SessionResponse:
    """Create a session AND pre-generate the scenario/task set.

    Synchronous on purpose: the frontend shows a briefing-loading state while
    this call is in flight, so the candidate never sees a "spinning UI in the
    workspace" state.
    """
    session = SessionModel(
        id=uuid4().hex,
        role=req.role,
        format=req.format,
        integrity_tier=req.integrity_tier,
        is_practice=req.is_practice,
        session_minutes=req.session_minutes,
        accessibility=req.accessibility.model_dump(),
        candidate_label=req.candidate_label,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    log_event(
        db,
        session=session,
        actor=Actor.SYSTEM,
        type="session_created",
        payload={
            "role": req.role,
            "format": req.format.value,
            "integrity_tier": req.integrity_tier.value,
            "is_practice": req.is_practice,
            "session_minutes": req.session_minutes,
        },
    )

    try:
        if req.format == SessionFormat.A:
            scenario = await scenario_gen(req.role)
            session.scenario_json = scenario.model_dump()
            log_payload = {
                "company_name": scenario.company_name,
                "task_count": len(scenario.tasks),
                "twist_trigger_turn": scenario.twist.trigger_after_turn,
            }
        else:
            task_set = await task_gen(req.role)
            session.scenario_json = task_set.model_dump()
            log_payload = {
                "company_name": task_set.company_name,
                "task_count": len(task_set.tasks),
            }
    except (ScenarioGenerationError, TaskSetGenerationError) as exc:
        log_event(
            db,
            session=session,
            actor=Actor.SYSTEM,
            type="scenario_generation_failed",
            payload={"error": str(exc), "format": req.format.value},
        )
        raise HTTPException(
            status_code=502,
            detail=f"Scenario generation failed: {exc}",
        ) from exc

    session.status = SessionStatus.BRIEFING
    db.add(session)
    db.commit()
    db.refresh(session)
    log_event(
        db,
        session=session,
        actor=Actor.SYSTEM,
        type="scenario_loaded",
        payload=log_payload,
    )
    return _to_response(session)


@app.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session_route(
    session_id: str, db: DbSession = Depends(get_session)
) -> SessionResponse:
    session = db.get(SessionModel, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return _to_response(session)


@app.post("/sessions/{session_id}/start", response_model=SessionResponse)
async def start_session(
    session_id: str, db: DbSession = Depends(get_session)
) -> SessionResponse:
    session = db.get(SessionModel, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status not in (SessionStatus.CREATED, SessionStatus.BRIEFING):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot start session in status {session.status.value}",
        )
    session.status = SessionStatus.ACTIVE
    session.started_at = datetime.now(timezone.utc)
    db.add(session)
    db.commit()
    db.refresh(session)
    log_event(db, session=session, actor=Actor.SYSTEM, type="session_start")
    return _to_response(session)


@app.post("/sessions/{session_id}/end", response_model=SessionResponse)
async def end_session(
    session_id: str,
    db: DbSession = Depends(get_session),
    evaluate_fn: EvaluateSessionFn = Depends(get_session_evaluator),
) -> SessionResponse:
    """End the session and run all rubric evaluators."""
    session = db.get(SessionModel, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status not in (SessionStatus.ACTIVE, SessionStatus.WRAPPING):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot end session in status {session.status.value}",
        )

    if session.ended_at is None:
        session.ended_at = datetime.now(timezone.utc)
    session.status = SessionStatus.WRAPPING
    db.add(session)
    db.commit()
    db.refresh(session)
    log_event(db, session=session, actor=Actor.SYSTEM, type="session_end")

    session.status = SessionStatus.SCORING
    db.add(session)
    db.commit()
    db.refresh(session)

    try:
        events = get_events(db, session.id)
        if not session.scenario_json:
            raise ScoringError("Session has no scenario; cannot score.")
        if session.format == SessionFormat.A:
            scenario_obj: Scenario | TaskSet = Scenario.model_validate(session.scenario_json)
        else:
            scenario_obj = TaskSet.model_validate(session.scenario_json)
        verdicts = await evaluate_fn(
            events=events, scenario_obj=scenario_obj, fmt=session.format
        )
    except Exception as exc:  # noqa: BLE001
        log_event(
            db,
            session=session,
            actor=Actor.SYSTEM,
            type="scoring_failed",
            payload={"error": str(exc)},
        )
        session.status = SessionStatus.WRAPPING
        db.add(session)
        db.commit()
        db.refresh(session)
        raise HTTPException(status_code=502, detail=f"Scoring failed: {exc}") from exc

    for v in verdicts:
        db.add(
            Scorecard(
                session_id=session.id,
                axis=v.axis,
                score_0_10=v.score_0_10,
                confidence_pm=v.confidence_pm,
                band=band_for(v.score_0_10),
                agreement=v.agreement,
                summary=v.summary,
                evidence=[e.model_dump() for e in v.evidence],
                flagged=v.flagged,
            )
        )
    log_event(
        db,
        session=session,
        actor=Actor.SYSTEM,
        type="scoring_complete",
        payload={"axes": [v.axis for v in verdicts]},
    )

    session.status = SessionStatus.COMPLETE
    db.add(session)
    db.commit()
    db.refresh(session)
    return _to_response(session)


# ============================================================================
# Scorecard + integrity
# ============================================================================


def _compute_integrity_context(events: list[Event]) -> IntegrityContextResponse:
    """Aggregate the integrity facts surfaced separately from scoring."""
    tab_lost = 0
    tab_away_ms = 0
    paste_count = 0
    paste_external_bytes = 0
    ai_turns = 0
    cast_msgs = 0
    for e in events:
        if e.type == "tab_focus_lost":
            tab_lost += 1
        elif e.type == "tab_focus_regained":
            tab_away_ms += int((e.payload or {}).get("away_ms", 0) or 0)
        elif e.type == "candidate_pasted_content":
            paste_count += 1
            if (e.payload or {}).get("source") == "external":
                paste_external_bytes += int((e.payload or {}).get("bytes", 0) or 0)
        elif e.type == "ai_assistant_query":
            ai_turns += 1
        elif e.type == "agent_message":
            cast_msgs += 1

    notes: list[str] = []
    if tab_lost == 0:
        notes.append("No tab switches observed.")
    else:
        notes.append(
            f"Tab focus left the session {tab_lost}× for a total of "
            f"{tab_away_ms // 1000}s — context only, not flagged."
        )
    if paste_count == 0:
        notes.append("No paste events observed.")
    else:
        notes.append(
            f"{paste_count} paste event(s); {paste_external_bytes} byte(s) "
            "from outside the session — context only, not flagged."
        )
    return IntegrityContextResponse(
        tab_focus_lost_count=tab_lost,
        tab_focus_total_away_ms=tab_away_ms,
        paste_event_count=paste_count,
        paste_external_bytes=paste_external_bytes,
        ai_assistant_turn_count=ai_turns,
        cast_message_count=cast_msgs,
        notes=notes,
    )


@app.get("/sessions/{session_id}/scorecard", response_model=ScorecardResponse)
async def get_scorecard(
    session_id: str, db: DbSession = Depends(get_session)
) -> ScorecardResponse:
    """Return the v3 evidence-cited scorecard for a session."""
    session = db.get(SessionModel, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    rows = list(
        db.exec(
            select(Scorecard)
            .where(Scorecard.session_id == session_id)
            .order_by(Scorecard.id)
        )
    )
    if not rows:
        raise HTTPException(
            status_code=404,
            detail="No scorecard yet — session may still be ACTIVE/WRAPPING.",
        )
    axes = [
        ScorecardAxisResponse(
            axis=r.axis,
            score_0_10=r.score_0_10,
            confidence_pm=r.confidence_pm,
            band=r.band,
            agreement=r.agreement,
            summary=r.summary,
            evidence=[
                ScorecardEvidenceResponse(
                    event_id=e["event_id"],
                    ts_ms=e["ts_ms"],
                    quote=e["quote"],
                    reasoning=e["reasoning"],
                )
                for e in (r.evidence or [])
            ],
            flagged=r.flagged,
        )
        for r in rows
    ]
    integrity = _compute_integrity_context(get_events(db, session_id))
    return ScorecardResponse(
        session_id=session_id,
        format=session.format,
        is_practice=session.is_practice,
        axes=axes,
        integrity=integrity,
    )


# ============================================================================
# Work-surface + AI assistant (Format A only)
# ============================================================================


@app.post(
    "/sessions/{session_id}/artifact",
    response_model=ArtifactSnapshotResponse,
    status_code=201,
)
async def post_artifact_snapshot(
    session_id: str,
    req: ArtifactSnapshotRequest,
    db: DbSession = Depends(get_session),
) -> ArtifactSnapshotResponse:
    session = db.get(SessionModel, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    event = log_event(
        db,
        session=session,
        actor=Actor.CANDIDATE,
        type="artifact_snapshot",
        payload={
            "filename": req.filename,
            "content": req.content,
            "trigger": req.trigger,
        },
    )
    return ArtifactSnapshotResponse(
        ts_ms=event.ts_ms, filename=req.filename, bytes=len(req.content)
    )


@app.post("/sessions/{session_id}/assistant", response_model=AssistantQueryResponse)
async def post_assistant_query(
    session_id: str,
    req: AssistantQueryRequest,
    db: DbSession = Depends(get_session),
    assistant_fn: AssistantReplyFn = Depends(get_assistant_reply),
) -> AssistantQueryResponse:
    """Run one AI-assistant turn. Format A only — Format B returns 409."""
    session = db.get(SessionModel, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.format != SessionFormat.A:
        raise HTTPException(
            status_code=409,
            detail=(
                "AI assistant is disabled in Format B (Solo Technical Assessment). "
                "Switch to Format A or take this session without it."
            ),
        )
    if not session.scenario_json:
        raise HTTPException(status_code=409, detail="Session has no scenario")
    scenario = Scenario.model_validate(session.scenario_json)

    events = get_events(db, session.id)
    transcript: list[dict] = []
    latest_artifact: str | None = None
    for ev in events:
        if not ev.payload:
            continue
        if ev.type == "ai_assistant_query":
            transcript.append({"role": "user", "content": ev.payload.get("content", "")})
        elif ev.type == "ai_assistant_response":
            transcript.append({"role": "assistant", "content": ev.payload.get("content", "")})
        elif ev.type == "artifact_snapshot":
            latest_artifact = ev.payload.get("content", "") or latest_artifact

    query_event = log_event(
        db,
        session=session,
        actor=Actor.CANDIDATE,
        type="ai_assistant_query",
        payload={"content": req.prompt},
    )

    try:
        response = await assistant_fn(
            scenario=scenario,
            latest_artifact=latest_artifact,
            transcript=transcript,
            query=req.prompt,
        )
    except Exception as exc:  # noqa: BLE001
        log_event(
            db,
            session=session,
            actor=Actor.SYSTEM,
            type="ai_assistant_error",
            payload={"error": str(exc)},
        )
        raise HTTPException(status_code=502, detail=f"Assistant failed: {exc}") from exc

    response_event = log_event(
        db,
        session=session,
        actor=Actor.AI_ASSISTANT,
        type="ai_assistant_response",
        payload={"content": response},
    )
    return AssistantQueryResponse(
        response=response,
        query_ts_ms=query_event.ts_ms,
        response_ts_ms=response_event.ts_ms,
    )


# ============================================================================
# Integrity events (§6.2 Standard tier — descriptive only)
# ============================================================================


@app.post("/sessions/{session_id}/integrity/tab-focus", status_code=201)
async def post_tab_focus_event(
    session_id: str,
    event: TabFocusEvent,
    db: DbSession = Depends(get_session),
) -> dict[str, int]:
    session = db.get(SessionModel, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    ev_type = "tab_focus_lost" if event.kind == "lost" else "tab_focus_regained"
    payload = {"away_ms": event.away_ms} if event.away_ms is not None else {}
    logged = log_event(
        db,
        session=session,
        actor=Actor.SYSTEM,
        type=ev_type,
        payload=payload,
    )
    return {"ts_ms": logged.ts_ms}


@app.post("/sessions/{session_id}/integrity/paste", status_code=201)
async def post_paste_event(
    session_id: str,
    req: PasteAttributionRequest,
    db: DbSession = Depends(get_session),
) -> dict[str, int]:
    session = db.get(SessionModel, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    logged = log_event(
        db,
        session=session,
        actor=Actor.CANDIDATE,
        type="candidate_pasted_content",
        payload={
            "target": req.target,
            "bytes": req.bytes,
            "source": req.source,
            "preview": req.preview,
        },
    )
    return {"ts_ms": logged.ts_ms}


# ============================================================================
# Right-to-explanation (§11.4)
# ============================================================================


_AXIS_EXPLANATIONS_A: list[AxisExplanation] = [
    AxisExplanation(
        axis="Judgment Under Ambiguity",
        plain_language=(
            "How you handled the under-specified parts of the brief: whether "
            "you asked clarifying questions, named your assumptions, and "
            "prioritized intelligently when scope exceeded time."
        ),
        what_we_measure=(
            "Specific moments where you surfaced ambiguity, asked the right "
            "person, made an assumption explicit, or chose what to drop."
        ),
        what_we_dont_measure=(
            "Speed in isolation, personality, or any inferred psychological trait."
        ),
    ),
    AxisExplanation(
        axis="Stakeholder Communication",
        plain_language=(
            "How you communicated with the PM, reviewer, and peer: clarity, "
            "channel-appropriateness, and constructive pushback where warranted."
        ),
        what_we_measure=(
            "The quality of disagreement when it occurred, not its presence. "
            "A calm reasonable execution without pushback is not penalized."
        ),
        what_we_dont_measure=(
            "Communication 'personality', warmth, charisma, or extraversion."
        ),
    ),
    AxisExplanation(
        axis="Response to Unexpected Change",
        plain_language=(
            "How you reacted when the PM changed a requirement mid-session: "
            "recognition, communication, replanning, and execution."
        ),
        what_we_measure=(
            "Whether you acknowledged the change, communicated its implications, "
            "and adjusted course."
        ),
        what_we_dont_measure=(
            "If the change never fired in your session, we explicitly do not "
            "score this axis against you."
        ),
    ),
    AxisExplanation(
        axis="Quality of AI Use",
        plain_language=(
            "Whether and how you used the in-app AI assistant. Using AI in "
            "Format A is allowed and expected; we measure quality, not presence."
        ),
        what_we_measure=(
            "Whether you used the assistant to verify and scaffold, retained "
            "ownership of decisions, and cross-checked AI output."
        ),
        what_we_dont_measure=(
            "Whether you used AI at all. Restraint is fine and is not bad."
        ),
    ),
    AxisExplanation(
        axis="Scope and Priority Management",
        plain_language=(
            "How you sequenced your work across the multi-task brief."
        ),
        what_we_measure=(
            "Whether you identified and finished the highest-leverage work "
            "and managed time across multiple tasks."
        ),
        what_we_dont_measure=(
            "Total volume of code written or characters typed."
        ),
    ),
    AxisExplanation(
        axis="Technical Execution",
        plain_language=(
            "The actual quality of the artifact you produced, calibrated to "
            "the role level being assessed."
        ),
        what_we_measure=(
            "Whether the code works, is professional-quality, and handles "
            "obvious edge cases reasonably."
        ),
        what_we_dont_measure=(
            "Style preference, idiom choice, or test framework choice."
        ),
    ),
]

_AXIS_EXPLANATIONS_B: list[AxisExplanation] = [
    AxisExplanation(
        axis="Technical Execution",
        plain_language=(
            "Whether your code works on the visible and hidden tests."
        ),
        what_we_measure=(
            "Correctness on the test cases at the role level being assessed."
        ),
        what_we_dont_measure=(
            "Style preference or unrelated code-style conventions."
        ),
    ),
    AxisExplanation(
        axis="Problem Decomposition and Approach",
        plain_language=(
            "Whether you identified the structure of the problem and chose a "
            "reasonable algorithm."
        ),
        what_we_measure=(
            "Algorithmic insight, complexity, and structural decomposition."
        ),
        what_we_dont_measure=(
            "Cleverness in isolation, or unnecessary virtuosity."
        ),
    ),
    AxisExplanation(
        axis="Code Quality",
        plain_language=(
            "Readability, structure, naming, idiom — at the role level."
        ),
        what_we_measure=(
            "Clarity and professional craftsmanship."
        ),
        what_we_dont_measure=(
            "Adherence to a single style convention over equivalent others."
        ),
    ),
    AxisExplanation(
        axis="Testing Discipline",
        plain_language=(
            "Whether you wrote or extended tests, handled edge cases, and "
            "verified before submitting."
        ),
        what_we_measure=(
            "Test coverage you authored and how you used the run loop."
        ),
        what_we_dont_measure=(
            "Whether your code passed every hidden test; we measure the "
            "discipline, not just the outcome."
        ),
    ),
    AxisExplanation(
        axis="Time Management Across Tasks",
        plain_language=(
            "How you sequenced and budgeted time across the multi-task set."
        ),
        what_we_measure=(
            "Whether you finished the most important tasks even if not all "
            "of them."
        ),
        what_we_dont_measure=(
            "How fast individual keystrokes were."
        ),
    ),
]


_RIGHTS = [
    "You may request a human review of this scorecard within 14 days.",
    "You may request an alternative assessment process via the hiring company.",
    "You may request a copy of your full session data.",
    "You may request deletion of your session data; we honor this within 30 days.",
    "You will never be auto-rejected based solely on Day One scoring. A human at "
    "the hiring company decides; our license forbids them from automating that.",
]

_SUB_PROCESSORS = [
    "Google Gemini API — model inference for the cast, the AI assistant, and "
    "evaluators. No retention of your prompts beyond what Google's API contract "
    "stipulates.",
    "SQLite (local) — your session data is stored in a single file on the "
    "hiring company's infrastructure for the duration of their retention "
    "contract (default: 24 months active).",
]


@app.get(
    "/sessions/{session_id}/explanation",
    response_model=ExplanationResponse,
)
async def get_explanation(
    session_id: str, db: DbSession = Depends(get_session)
) -> ExplanationResponse:
    session = db.get(SessionModel, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    per_axis = (
        _AXIS_EXPLANATIONS_A
        if session.format == SessionFormat.A
        else _AXIS_EXPLANATIONS_B
    )
    intro = (
        "This page explains what we measured in your Day One session, "
        "what we did not measure, and your rights. Every axis on your "
        "scorecard cites specific moments from the event log — you can "
        "see the same evidence the human reviewer sees."
    )
    return ExplanationResponse(
        session_id=session_id,
        format=session.format,
        intro=intro,
        per_axis=per_axis,
        rights=_RIGHTS,
        sub_processors=_SUB_PROCESSORS,
    )


# ============================================================================
# Appeal (§11.5)
# ============================================================================


@app.post("/sessions/{session_id}/appeal", response_model=AppealResponse, status_code=201)
async def post_appeal(
    session_id: str,
    req: AppealRequest,
    db: DbSession = Depends(get_session),
) -> AppealResponse:
    session = db.get(SessionModel, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    appeal = Appeal(session_id=session_id, reason=req.reason)
    db.add(appeal)
    db.commit()
    db.refresh(appeal)
    log_event(
        db,
        session=session,
        actor=Actor.SYSTEM,
        type="appeal_submitted",
        payload={"appeal_id": appeal.id},
    )
    return AppealResponse(
        id=appeal.id,  # type: ignore[arg-type]
        session_id=appeal.session_id,
        status=appeal.status,
        created_at=appeal.created_at,
    )


# ============================================================================
# Event log (debug surface)
# ============================================================================


@app.get(
    "/sessions/{session_id}/events",
    response_model=list[EventResponse],
)
async def list_session_events(
    session_id: str,
    db: DbSession = Depends(get_session),
) -> list[EventResponse]:
    session = db.get(SessionModel, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    events = get_events(db, session.id)
    return [
        EventResponse(
            id=e.id,  # type: ignore[arg-type]
            session_id=e.session_id,
            ts_ms=e.ts_ms,
            ts_abs=e.ts_abs,
            actor=e.actor,
            type=e.type,
            payload=e.payload,
        )
        for e in events
    ]


# ============================================================================
# Recruiter dashboard (§12.1)
# ============================================================================


@app.get("/recruiter/sessions", response_model=list[RecruiterSessionRow])
async def list_recruiter_sessions(
    db: DbSession = Depends(get_session),
) -> list[RecruiterSessionRow]:
    rows = list(
        db.exec(
            select(SessionModel)
            .where(SessionModel.is_practice == False)  # noqa: E712 — SQLModel comparison
            .order_by(SessionModel.created_at.desc())  # type: ignore[union-attr]
            .limit(50)
        )
    )
    out: list[RecruiterSessionRow] = []
    for s in rows:
        scores = list(
            db.exec(
                select(Scorecard)
                .where(Scorecard.session_id == s.id)
                .order_by(Scorecard.id)
            )
        )
        out.append(
            RecruiterSessionRow(
                id=s.id,
                role=s.role,
                format=s.format,
                status=s.status,
                candidate_label=s.candidate_label,
                is_practice=s.is_practice,
                started_at=s.started_at,
                ended_at=s.ended_at,
                axes_summary=[
                    {
                        "axis": r.axis,
                        "score_0_10": r.score_0_10,
                        "band": r.band,
                        "flagged": r.flagged,
                    }
                    for r in scores
                ],
            )
        )
    return out


# ============================================================================
# WebSocket — Format A only
# ============================================================================


TWIST_FOLLOW_UP_DELAY_S = 1.2


@app.websocket("/sessions/{session_id}/ws")
async def session_ws(websocket: WebSocket, session_id: str) -> None:
    """Per-session orchestrator socket (Format A only)."""
    await websocket.accept()

    with DbSession(engine) as db:
        session = db.get(SessionModel, session_id)
        if session is None:
            await websocket.send_json({"type": "error", "message": "Session not found"})
            await websocket.close()
            return
        if session.format != SessionFormat.A:
            await websocket.send_json(
                {
                    "type": "error",
                    "message": "Cast chat is only available in Format A.",
                }
            )
            await websocket.close()
            return
        if not session.scenario_json:
            await websocket.send_json(
                {"type": "error", "message": "Session has no scenario; cannot start chat"}
            )
            await websocket.close()
            return
        scenario = Scenario.model_validate(session.scenario_json)
        orchestrator = SessionOrchestrator.from_event_log(
            db=db, session=session, scenario=scenario
        )
        history = {ch: history_for_channel(get_events(db, session.id), ch) for ch in CHANNELS}

    await websocket.send_json({"type": "ready", "history": history})

    try:
        while True:
            msg = await websocket.receive_json()
            mtype = msg.get("type")

            if mtype != "candidate_message":
                await websocket.send_json(
                    {"type": "error", "message": f"Unknown message type: {mtype!r}"}
                )
                continue

            channel = msg.get("channel")
            content = (msg.get("content") or "").strip()
            if channel not in CHANNELS:
                await websocket.send_json(
                    {"type": "error", "message": f"Unknown channel: {channel!r}"}
                )
                continue
            if not content:
                await websocket.send_json(
                    {"type": "error", "message": "Empty message ignored"}
                )
                continue

            await websocket.send_json(
                {"type": "typing", "channel": channel, "is_typing": True}
            )

            try:
                with DbSession(engine) as db:
                    session = db.get(SessionModel, session_id)
                    if session is None:
                        await websocket.send_json(
                            {"type": "error", "message": "Session disappeared"}
                        )
                        break
                    outcome = await orchestrator.handle_candidate_message(
                        db=db, session=session, channel=channel, content=content
                    )
            except Exception as exc:  # noqa: BLE001
                await websocket.send_json(
                    {"type": "typing", "channel": channel, "is_typing": False}
                )
                await websocket.send_json(
                    {"type": "error", "message": f"Reply failed: {exc}"}
                )
                continue

            await websocket.send_json(
                {"type": "typing", "channel": channel, "is_typing": False}
            )
            await websocket.send_json(
                {
                    "type": "agent_message",
                    "channel": channel,
                    "actor_name": outcome.actor_name,
                    "content": outcome.reply,
                    "ts_ms": outcome.reply_ts_ms,
                }
            )

            if outcome.twist is not None:
                await asyncio.sleep(TWIST_FOLLOW_UP_DELAY_S)
                await websocket.send_json(
                    {
                        "type": "requirement_change",
                        "channel": "pm",
                        "actor_name": outcome.twist["actor_name"],
                        "content": outcome.twist["content"],
                        "summary": outcome.twist["summary"],
                        "ts_ms": outcome.twist["ts_ms"],
                    }
                )
    except WebSocketDisconnect:
        return
