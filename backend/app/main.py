"""FastAPI entrypoint — health, session lifecycle, scenario-on-create.

Phase 1: session CRUD + telemetry.
Phase 2: POST /sessions also generates a fictional scenario (strong-tier
         Gemini call) and stores it on the session before returning. Done
         synchronously so the latency is hidden behind the Briefing screen.
Phase 3 will add the WebSocket endpoint; Phase 5 adds /scorecard.
"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Awaitable, Callable
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session as DbSession

from app.agents.assistant import assistant_reply as _default_assistant_reply
from app.agents.scenario_engine import (
    Scenario,
    ScenarioGenerationError,
    generate_scenario,
)
from app.config import settings
from app.db import engine, get_session, init_db
from app.models import Actor, Session as SessionModel, SessionStatus
from app.orchestrator import CHANNELS, SessionOrchestrator, history_for_channel
from app.schemas import (
    ArtifactSnapshotRequest,
    ArtifactSnapshotResponse,
    AssistantQueryRequest,
    AssistantQueryResponse,
    CreateSessionRequest,
    EventResponse,
    SessionResponse,
)
from app.telemetry import get_events, log_event

AssistantReplyFn = Callable[..., Awaitable[str]]

# Callable signature: (role: str) -> awaitable Scenario.
ScenarioGenerator = Callable[[str], Awaitable[Scenario]]


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Day One", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_scenario_generator() -> ScenarioGenerator:
    """Dependency providing the scenario generator.

    Test code overrides this with a deterministic fake via
    `app.dependency_overrides[get_scenario_generator] = ...`.
    """
    return generate_scenario


def get_assistant_reply() -> AssistantReplyFn:
    """Dependency providing the AI assistant reply function.

    Test code overrides this with a fake to avoid LLM calls.
    """
    return _default_assistant_reply


def _to_response(s: SessionModel) -> SessionResponse:
    return SessionResponse(
        id=s.id,
        role=s.role,
        status=s.status,
        scenario=s.scenario_json or {},
        created_at=s.created_at,
        started_at=s.started_at,
        ended_at=s.ended_at,
    )


# ---------- health ----------

@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "day-one", "version": app.version}


# ---------- sessions ----------

@app.post("/sessions", response_model=SessionResponse, status_code=201)
async def create_session(
    req: CreateSessionRequest,
    db: DbSession = Depends(get_session),
    gen: ScenarioGenerator = Depends(get_scenario_generator),
) -> SessionResponse:
    """Create a session AND pre-generate the scenario.

    Synchronous on purpose: the frontend shows a briefing-loading state while
    this call is in flight, so the candidate never sees a "spinning UI in the
    workspace" state.
    """
    session = SessionModel(id=uuid4().hex, role=req.role)
    db.add(session)
    db.commit()
    db.refresh(session)
    log_event(
        db,
        session=session,
        actor=Actor.SYSTEM,
        type="session_created",
        payload={"role": req.role},
    )

    try:
        scenario = await gen(req.role)
    except ScenarioGenerationError as exc:
        log_event(
            db,
            session=session,
            actor=Actor.SYSTEM,
            type="scenario_generation_failed",
            payload={"error": str(exc)},
        )
        raise HTTPException(
            status_code=502,
            detail=f"Scenario generation failed: {exc}",
        ) from exc

    session.scenario_json = scenario.model_dump()
    session.status = SessionStatus.BRIEFING
    db.add(session)
    db.commit()
    db.refresh(session)
    log_event(
        db,
        session=session,
        actor=Actor.SYSTEM,
        type="scenario_loaded",
        payload={
            "company_name": scenario.company_name,
            "task_count": len(scenario.tasks),
            "twist_trigger_turn": scenario.twist.trigger_after_turn,
        },
    )
    return _to_response(session)


@app.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session_route(
    session_id: str,
    db: DbSession = Depends(get_session),
) -> SessionResponse:
    session = db.get(SessionModel, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return _to_response(session)


@app.post("/sessions/{session_id}/start", response_model=SessionResponse)
async def start_session(
    session_id: str,
    db: DbSession = Depends(get_session),
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
) -> SessionResponse:
    session = db.get(SessionModel, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status not in (SessionStatus.ACTIVE, SessionStatus.WRAPPING):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot end session in status {session.status.value}",
        )
    # WRAPPING marks "candidate is done; evaluators have not finished yet".
    # Phase 5 transitions WRAPPING → SCORING → COMPLETE.
    session.status = SessionStatus.WRAPPING
    session.ended_at = datetime.now(timezone.utc)
    db.add(session)
    db.commit()
    db.refresh(session)
    log_event(db, session=session, actor=Actor.SYSTEM, type="session_end")
    return _to_response(session)


# ---------- work-surface telemetry + AI assistant ----------


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
    """Log a snapshot of the candidate's current work surface.

    Frontend calls this:
      - on debounced typing (~3-5s of inactivity), trigger="debounce"
      - on an explicit save/send action, trigger="send"
    Each call appends an `artifact_snapshot` event. Evaluators in Phase 5
    will read these to understand how the artifact evolved.
    """
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


@app.post(
    "/sessions/{session_id}/assistant",
    response_model=AssistantQueryResponse,
)
async def post_assistant_query(
    session_id: str,
    req: AssistantQueryRequest,
    db: DbSession = Depends(get_session),
    assistant_fn: AssistantReplyFn = Depends(get_assistant_reply),
) -> AssistantQueryResponse:
    """Run one AI-assistant turn.

    Every query and every response is logged as a telemetry event — this is
    what feeds the "Quality of AI Use" rubric axis in Phase 5.

    The assistant sees:
      - the session scenario (role + tasks),
      - the candidate's most recent `artifact_snapshot` (their working file),
      - the prior assistant turns in this session (so it has memory).
    """
    session = db.get(SessionModel, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.scenario_json:
        raise HTTPException(status_code=409, detail="Session has no scenario")
    scenario = Scenario.model_validate(session.scenario_json)

    # Reconstruct prior assistant transcript + latest artifact from event log.
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

    # Log the query FIRST so it appears before the response in the event log.
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


@app.get(
    "/sessions/{session_id}/events",
    response_model=list[EventResponse],
)
async def list_session_events(
    session_id: str,
    db: DbSession = Depends(get_session),
) -> list[EventResponse]:
    """Full event log for a session — ordered story used by Phase 5 evaluators."""
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


# ---------- websocket: per-session orchestrator ----------

# Small delay between an agent's regular reply and a twist follow-up, so the
# twist feels like a separate Slack ping rather than glued to the reply.
TWIST_FOLLOW_UP_DELAY_S = 1.2


@app.websocket("/sessions/{session_id}/ws")
async def session_ws(websocket: WebSocket, session_id: str) -> None:
    """Per-session orchestrator socket.

    Protocol (JSON frames):

        Client → Server:
            {"type": "candidate_message", "channel": "pm"|"reviewer"|"teammate", "content": "..."}

        Server → Client:
            {"type": "ready", "history": {channel: [<message>, ...]}}
            {"type": "typing", "channel": str, "is_typing": bool}
            {"type": "agent_message", "channel": str, "actor_name": str, "content": str, "ts_ms": int}
            {"type": "requirement_change", "channel": "pm", "actor_name": str, "content": str, "summary": str, "ts_ms": int}
            {"type": "error", "message": str}
    """
    await websocket.accept()

    # Initial handshake: load session, build orchestrator, send history.
    with DbSession(engine) as db:
        session = db.get(SessionModel, session_id)
        if session is None:
            await websocket.send_json({"type": "error", "message": "Session not found"})
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

            # Typing indicator — sent immediately so the candidate sees life.
            await websocket.send_json(
                {"type": "typing", "channel": channel, "is_typing": True}
            )

            # Run the orchestrator turn against a short-lived DB session.
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
                # Small natural pause then a separate PM ping for the twist.
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
