"""Integration tests for the session lifecycle, both Formats (v3)."""
from __future__ import annotations

import pytest
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


@pytest.mark.parametrize("fmt", ["A", "B"])
def test_full_session_lifecycle_per_format(fmt: str) -> None:
    client = TestClient(app)

    payload = {
        "role": "Junior Full-Stack Developer",
        "format": fmt,
        "session_minutes": 60,
        "integrity_tier": "standard",
        "accessibility": {
            "mode_enabled": False,
            "extended_time_multiplier": 1.0,
            "reduced_motion": False,
            "high_contrast": False,
            "dyslexia_font": False,
            "screen_reader_optimized": False,
        },
        "is_practice": False,
    }
    r = client.post("/sessions", json=payload)
    assert r.status_code == 201, r.text
    body = r.json()
    sid = body["id"]
    assert body["status"] == SessionStatus.BRIEFING.value
    assert body["format"] == fmt
    assert body["scenario"]["company_name"] == "TestCo"
    assert body["scenario"]["role"] == "Junior Full-Stack Developer"
    assert body["started_at"] is None
    assert body["ended_at"] is None

    # Format-specific shape sanity
    if fmt == "A":
        assert "cast" in body["scenario"]
        assert "twist" in body["scenario"]
        assert "starter_artifact" in body["scenario"]
    else:
        assert "cast" not in body["scenario"]
        for t in body["scenario"]["tasks"]:
            assert "starter_code" in t
            assert "visible_tests" in t

    # start
    r = client.post(f"/sessions/{sid}/start")
    assert r.status_code == 200
    assert r.json()["status"] == SessionStatus.ACTIVE.value

    # end → scoring → COMPLETE
    r = client.post(f"/sessions/{sid}/end")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == SessionStatus.COMPLETE.value

    events = _events_for(sid)
    types = [e.type for e in events]
    assert "session_created" in types
    assert "scenario_loaded" in types
    assert "session_start" in types
    assert "session_end" in types
    assert "scoring_complete" in types


def test_get_missing_session_returns_404() -> None:
    client = TestClient(app)
    r = client.get("/sessions/does-not-exist")
    assert r.status_code == 404


def test_start_already_started_session_conflicts() -> None:
    client = TestClient(app)
    sid = client.post(
        "/sessions",
        json={"role": "Junior Full-Stack Developer", "format": "A"},
    ).json()["id"]
    client.post(f"/sessions/{sid}/start")
    r = client.post(f"/sessions/{sid}/start")
    assert r.status_code == 409


def test_format_b_assistant_route_returns_409() -> None:
    """AI assistant is disabled in Format B by design."""
    client = TestClient(app)
    sid = client.post(
        "/sessions",
        json={"role": "Junior Full-Stack Developer", "format": "B"},
    ).json()["id"]
    client.post(f"/sessions/{sid}/start")
    r = client.post(f"/sessions/{sid}/assistant", json={"prompt": "help"})
    assert r.status_code == 409
    assert "format b" in r.json()["detail"].lower()
