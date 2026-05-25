"""WebSocket integration tests for the orchestrator route.

cast_reply is monkeypatched to a deterministic fake so we exercise the WS
protocol (handshake → typing → agent_message → twist) without LLM calls.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app.orchestrator as orchestrator_module
from app.main import app


async def _fake_reply(*, scenario, channel, transcript, twist_fired):
    suffix = " (post-twist)" if twist_fired else ""
    return f"[{channel}] ack #{len(transcript)}{suffix}"


@pytest.fixture
def patch_cast_reply(monkeypatch):
    """Swap the orchestrator's default cast_reply for the fake."""
    monkeypatch.setattr(orchestrator_module, "default_cast_reply", _fake_reply)
    yield


def _drain_until(ws, predicate, *, max_frames: int = 10):
    """Pull frames until predicate(frame) is True; returns the frame."""
    for _ in range(max_frames):
        frame = ws.receive_json()
        if predicate(frame):
            return frame
    raise AssertionError("predicate not matched within max_frames")


def test_ws_full_flow_pm_then_twist_then_reviewer(patch_cast_reply) -> None:
    client = TestClient(app)
    sid = client.post("/sessions", json={"role": "Junior Full-Stack Developer"}).json()["id"]
    client.post(f"/sessions/{sid}/start")

    with client.websocket_connect(f"/sessions/{sid}/ws") as ws:
        # Initial handshake.
        ready = ws.receive_json()
        assert ready["type"] == "ready"
        assert set(ready["history"].keys()) == {"pm", "reviewer", "peer"}

        # Send 3 candidate messages to #pm (fake scenario triggers twist at turn 3).
        for i in (1, 2, 3):
            ws.send_json(
                {"type": "candidate_message", "channel": "pm", "content": f"pm message {i}"}
            )
            # typing on
            t_on = ws.receive_json()
            assert t_on == {"type": "typing", "channel": "pm", "is_typing": True}
            # typing off
            t_off = _drain_until(ws, lambda f: f.get("type") == "typing" and not f.get("is_typing"))
            assert t_off["channel"] == "pm"
            # agent_message
            agent = ws.receive_json()
            assert agent["type"] == "agent_message"
            assert agent["channel"] == "pm"
            assert agent["actor_name"]
            assert "ack" in agent["content"]

            # On turn 3 we ALSO expect a requirement_change frame.
            if i == 3:
                twist = _drain_until(
                    ws, lambda f: f.get("type") == "requirement_change", max_frames=5
                )
                assert twist["channel"] == "pm"
                assert twist["summary"]
                assert twist["content"]

        # Now a message to #reviewer — twist should already have fired, so
        # the fake reply should mention "post-twist".
        ws.send_json(
            {
                "type": "candidate_message",
                "channel": "reviewer",
                "content": "what do you think of my approach?",
            }
        )
        ws.receive_json()  # typing on
        _drain_until(ws, lambda f: f.get("type") == "typing" and not f.get("is_typing"))
        agent = ws.receive_json()
        assert agent["type"] == "agent_message"
        assert agent["channel"] == "reviewer"
        assert "post-twist" in agent["content"]


def test_ws_rejects_unknown_channel(patch_cast_reply) -> None:
    client = TestClient(app)
    sid = client.post("/sessions", json={"role": "Junior Full-Stack Developer"}).json()["id"]
    client.post(f"/sessions/{sid}/start")

    with client.websocket_connect(f"/sessions/{sid}/ws") as ws:
        ws.receive_json()  # ready
        ws.send_json({"type": "candidate_message", "channel": "nope", "content": "x"})
        err = ws.receive_json()
        assert err["type"] == "error"
        assert "channel" in err["message"].lower()


def test_ws_rejects_unknown_session() -> None:
    client = TestClient(app)
    with client.websocket_connect("/sessions/does-not-exist/ws") as ws:
        err = ws.receive_json()
        assert err["type"] == "error"
        assert "not found" in err["message"].lower()
