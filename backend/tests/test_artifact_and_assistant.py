"""Phase 4 — work-surface telemetry + AI assistant tests.

We assert:
  - artifact snapshots land in the event log with the right payload + trigger
  - the assistant route logs BOTH query and response events
  - multi-turn assistant: prior turns are visible to the assistant fn
  - GET /sessions/{id}/events returns a coherent, ordered timeline that mixes
    chat, artifact snapshots, and assistant turns
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.db import engine
from app.main import app, get_assistant_reply
from app.models import Event
from sqlmodel import Session as DbSession, select


_assistant_calls: list[dict] = []


async def _fake_assistant_reply(*, scenario, latest_artifact, transcript, query):
    _assistant_calls.append(
        {
            "query": query,
            "latest_artifact": latest_artifact,
            "transcript_len": len(transcript),
        }
    )
    return f"FAKE: artifact_bytes={len(latest_artifact or '')}, prior_turns={len(transcript)}, q={query[:40]}"


def _override_assistant():
    return _fake_assistant_reply


app.dependency_overrides[get_assistant_reply] = _override_assistant


@pytest.fixture(autouse=True)
def _reset_calls():
    _assistant_calls.clear()
    yield


def _all_events(session_id: str) -> list[Event]:
    with DbSession(engine) as db:
        return list(
            db.exec(select(Event).where(Event.session_id == session_id).order_by(Event.id))
        )


def test_artifact_snapshot_logs_event() -> None:
    client = TestClient(app)
    sid = client.post("/sessions", json={"role": "Junior Full-Stack Developer"}).json()["id"]
    client.post(f"/sessions/{sid}/start")

    r = client.post(
        f"/sessions/{sid}/artifact",
        json={
            "filename": "main.py",
            "content": "def hello():\n    return 'world'\n",
            "trigger": "debounce",
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["filename"] == "main.py"
    assert body["bytes"] == len("def hello():\n    return 'world'\n")

    events = _all_events(sid)
    snaps = [e for e in events if e.type == "artifact_snapshot"]
    assert len(snaps) == 1
    assert snaps[0].payload["filename"] == "main.py"
    assert snaps[0].payload["trigger"] == "debounce"
    assert "hello" in snaps[0].payload["content"]


def test_assistant_route_logs_query_and_response() -> None:
    client = TestClient(app)
    sid = client.post("/sessions", json={"role": "Junior Full-Stack Developer"}).json()["id"]
    client.post(f"/sessions/{sid}/start")

    r = client.post(
        f"/sessions/{sid}/assistant",
        json={"prompt": "How do I validate an enum in Pydantic?"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["response"].startswith("FAKE:")
    assert body["query_ts_ms"] <= body["response_ts_ms"]

    events = _all_events(sid)
    types = [e.type for e in events]
    # Order matters: query must appear before response in the timeline.
    assert types.index("ai_assistant_query") < types.index("ai_assistant_response")

    # Assistant received empty artifact (no snapshot yet) and empty transcript.
    assert _assistant_calls[-1]["latest_artifact"] is None
    assert _assistant_calls[-1]["transcript_len"] == 0


def test_assistant_sees_latest_artifact_and_prior_turns() -> None:
    client = TestClient(app)
    sid = client.post("/sessions", json={"role": "Junior Full-Stack Developer"}).json()["id"]
    client.post(f"/sessions/{sid}/start")

    # Two snapshots — the assistant should see the LATEST one only.
    client.post(
        f"/sessions/{sid}/artifact",
        json={"filename": "main.py", "content": "v1", "trigger": "debounce"},
    )
    client.post(
        f"/sessions/{sid}/artifact",
        json={"filename": "main.py", "content": "v2 = better", "trigger": "send"},
    )

    # First assistant turn.
    client.post(f"/sessions/{sid}/assistant", json={"prompt": "First question"})
    # Second assistant turn — should see prior turn (1 user + 1 assistant = 2 messages).
    client.post(f"/sessions/{sid}/assistant", json={"prompt": "Follow up"})

    assert _assistant_calls[0]["latest_artifact"] == "v2 = better"
    assert _assistant_calls[0]["transcript_len"] == 0
    assert _assistant_calls[1]["latest_artifact"] == "v2 = better"
    assert _assistant_calls[1]["transcript_len"] == 2  # user1 + assistant1


def test_events_route_returns_coherent_ordered_timeline() -> None:
    client = TestClient(app)
    sid = client.post("/sessions", json={"role": "Junior Full-Stack Developer"}).json()["id"]
    client.post(f"/sessions/{sid}/start")

    # Mix of activity.
    client.post(
        f"/sessions/{sid}/artifact",
        json={"filename": "main.py", "content": "x = 1", "trigger": "debounce"},
    )
    client.post(f"/sessions/{sid}/assistant", json={"prompt": "what does x mean?"})
    client.post(
        f"/sessions/{sid}/artifact",
        json={"filename": "main.py", "content": "x = 2", "trigger": "send"},
    )
    client.post(f"/sessions/{sid}/end")

    r = client.get(f"/sessions/{sid}/events")
    assert r.status_code == 200
    events = r.json()
    types = [e["type"] for e in events]

    # Story sanity: session_created, scenario_loaded, session_start come first;
    # then mixed candidate activity; ending with scoring_complete (Phase 5
    # wires scoring into /end, so session_end is followed by scoring_complete).
    assert types[0] == "session_created"
    assert "scenario_loaded" in types
    assert "session_start" in types
    assert "session_end" in types
    assert types[-1] == "scoring_complete"

    # ts_ms monotonically non-decreasing (events are ordered by ts_ms then id).
    ts_list = [e["ts_ms"] for e in events]
    assert ts_list == sorted(ts_list)

    # Multi-snapshot + assistant Q/A both present.
    snap_count = sum(1 for t in types if t == "artifact_snapshot")
    assert snap_count == 2
    assert types.count("ai_assistant_query") == 1
    assert types.count("ai_assistant_response") == 1


def test_artifact_route_404s_on_missing_session() -> None:
    client = TestClient(app)
    r = client.post(
        "/sessions/nope/artifact",
        json={"filename": "x.py", "content": "y = 1", "trigger": "debounce"},
    )
    assert r.status_code == 404


def test_assistant_route_404s_on_missing_session() -> None:
    client = TestClient(app)
    r = client.post("/sessions/nope/assistant", json={"prompt": "hi"})
    assert r.status_code == 404
