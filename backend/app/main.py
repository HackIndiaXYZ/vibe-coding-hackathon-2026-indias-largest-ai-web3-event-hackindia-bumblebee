"""FastAPI entrypoint — health + session lifecycle REST routes.

Phase 1 covers session CRUD and the foundation for telemetry. Phase 3 adds the
WebSocket endpoint for the orchestrator; Phase 5 adds /scorecard.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session as DbSession

from app.config import settings
from app.db import get_session, init_db
from app.models import Actor, Session as SessionModel, SessionStatus
from app.schemas import CreateSessionRequest, SessionResponse
from app.telemetry import log_event


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
) -> SessionResponse:
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
    # Scenario generation will be wired in Phase 2 (synchronously here, since
    # we want to hide its latency behind the briefing screen).
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
