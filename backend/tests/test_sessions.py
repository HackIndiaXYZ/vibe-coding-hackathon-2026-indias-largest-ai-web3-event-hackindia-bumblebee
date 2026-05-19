"""Integration tests for the session lifecycle: create → get → start → end.

Also asserts that telemetry events fire at each lifecycle transition, since
the rest of the system depends on a reliable event log.
"""
from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import Session as DbSession, select

from app.db import engine
from app.main import app
from app.models import Event, SessionStatus


def _events_for(session_id: str) -> list[Event]:
    with DbSession(engine) as db:
        return list(
            db.exec(select(Event).where(Event.session_id == session_id).order_by(Event.id))
        )


def test_full_session_lifecycle() -> None:
    client = TestClient(app)

    # create
    r = client.post("/sessions", json={"role": "Junior Full-Stack Developer"})
    assert r.status_code == 201, r.text
    body = r.json()
    sid = body["id"]
    assert body["status"] == SessionStatus.CREATED.value
    assert body["role"] == "Junior Full-Stack Developer"
    assert body["started_at"] is None
    assert body["ended_at"] is None

    # get
    r = client.get(f"/sessions/{sid}")
    assert r.status_code == 200
    assert r.json()["id"] == sid

    # start
    r = client.post(f"/sessions/{sid}/start")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == SessionStatus.ACTIVE.value
    assert body["started_at"] is not None

    # end
    r = client.post(f"/sessions/{sid}/end")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == SessionStatus.WRAPPING.value
    assert body["ended_at"] is not None

    # telemetry: should have created, start, end events
    events = _events_for(sid)
    types = [e.type for e in events]
    assert "session_created" in types
    assert "session_start" in types
    assert "session_end" in types


def test_get_missing_session_returns_404() -> None:
    client = TestClient(app)
    r = client.get("/sessions/does-not-exist")
    assert r.status_code == 404


def test_start_already_started_session_conflicts() -> None:
    client = TestClient(app)
    sid = client.post("/sessions", json={"role": "Junior Full-Stack Developer"}).json()["id"]
    client.post(f"/sessions/{sid}/start")
    r = client.post(f"/sessions/{sid}/start")
    assert r.status_code == 409
