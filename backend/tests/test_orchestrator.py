"""Orchestrator unit tests — no LLM required.

We inject a deterministic fake cast_reply so the orchestrator's state machine
(channel routing, transcript bookkeeping, twist firing, event logging) is
tested independently of the model. Phase 3's WS integration test exercises
the full path.
"""
from __future__ import annotations

import pytest
from sqlmodel import Session as DbSession

from app.db import engine
from app.models import Session as SessionModel, SessionStatus
from app.orchestrator import SessionOrchestrator
from app.telemetry import get_events
from tests.conftest import _build_fake_scenario


async def _fake_reply(*, scenario, channel, transcript, twist_fired):
    base = f"[{channel}] ack:{len(transcript)}"
    if twist_fired:
        base += " (post-twist)"
    return base


def _make_active_session(role: str = "Junior Full-Stack Developer") -> SessionModel:
    scenario = _build_fake_scenario(role)
    with DbSession(engine) as db:
        s = SessionModel(
            id="orch-test-1",
            role=role,
            scenario_json=scenario.model_dump(),
            status=SessionStatus.ACTIVE,
        )
        from datetime import datetime, timezone

        s.started_at = datetime.now(timezone.utc)
        db.add(s)
        db.commit()
        db.refresh(s)
    return s


async def test_pm_turn_routing_and_event_log() -> None:
    session = _make_active_session()
    scenario = _build_fake_scenario(session.role)
    orch = SessionOrchestrator(scenario=scenario, cast_reply_fn=_fake_reply)

    with DbSession(engine) as db:
        s = db.get(SessionModel, session.id)
        outcome = await orch.handle_candidate_message(
            db=db, session=s, channel="pm", content="Hello PM"
        )

    assert outcome.reply.startswith("[pm] ack:")
    assert outcome.actor_name == scenario.cast.pm.name
    assert outcome.twist is None  # turn 1 of trigger=3 → not yet

    with DbSession(engine) as db:
        events = get_events(db, session.id)
    types = [e.type for e in events]
    assert "candidate_message" in types
    assert "agent_message" in types
    assert "requirement_change" not in types


async def test_twist_fires_on_third_pm_turn_then_does_not_refire() -> None:
    session = _make_active_session(role="Twist Test Role")
    scenario = _build_fake_scenario(session.role)  # twist.trigger_after_turn = 3
    orch = SessionOrchestrator(scenario=scenario, cast_reply_fn=_fake_reply)

    # Turns 1 and 2 → no twist.
    for i in (1, 2):
        with DbSession(engine) as db:
            s = db.get(SessionModel, session.id)
            outcome = await orch.handle_candidate_message(
                db=db, session=s, channel="pm", content=f"msg {i}"
            )
        assert outcome.twist is None, f"twist fired prematurely on turn {i}"

    # Turn 3 → twist fires.
    with DbSession(engine) as db:
        s = db.get(SessionModel, session.id)
        outcome = await orch.handle_candidate_message(
            db=db, session=s, channel="pm", content="msg 3"
        )
    assert outcome.twist is not None
    assert outcome.twist["summary"] == scenario.twist.summary
    assert outcome.twist["content"] == scenario.twist.pm_message
    assert orch.twist_fired is True

    # Turn 4 → twist does NOT re-fire; reply is post-twist.
    with DbSession(engine) as db:
        s = db.get(SessionModel, session.id)
        outcome = await orch.handle_candidate_message(
            db=db, session=s, channel="pm", content="msg 4"
        )
    assert outcome.twist is None
    assert "post-twist" in outcome.reply

    with DbSession(engine) as db:
        events = get_events(db, session.id)
    type_counts = {t: sum(1 for e in events if e.type == t) for t in {e.type for e in events}}
    assert type_counts.get("requirement_change", 0) == 1, "twist should only fire once"


async def test_reviewer_channel_does_not_trigger_twist() -> None:
    session = _make_active_session(role="Reviewer Test")
    scenario = _build_fake_scenario(session.role)
    orch = SessionOrchestrator(scenario=scenario, cast_reply_fn=_fake_reply)

    for i in range(5):  # 5 reviewer turns
        with DbSession(engine) as db:
            s = db.get(SessionModel, session.id)
            outcome = await orch.handle_candidate_message(
                db=db, session=s, channel="reviewer", content=f"reviewer msg {i}"
            )
        assert outcome.twist is None
    assert orch.twist_fired is False


async def test_orchestrator_rehydrates_state_from_event_log() -> None:
    """Simulate a reconnect: build fresh orchestrator from DB and verify state."""
    session = _make_active_session(role="Rehydration Test")
    scenario = _build_fake_scenario(session.role)
    orch = SessionOrchestrator(scenario=scenario, cast_reply_fn=_fake_reply)

    # Run 3 pm turns + 1 reviewer turn (will fire twist on pm turn 3).
    for i in range(3):
        with DbSession(engine) as db:
            s = db.get(SessionModel, session.id)
            await orch.handle_candidate_message(
                db=db, session=s, channel="pm", content=f"pm{i}"
            )
    with DbSession(engine) as db:
        s = db.get(SessionModel, session.id)
        await orch.handle_candidate_message(
            db=db, session=s, channel="reviewer", content="rev0"
        )

    # Fresh orchestrator, reconstructed from event log.
    with DbSession(engine) as db:
        s = db.get(SessionModel, session.id)
        rebuilt = SessionOrchestrator.from_event_log(
            db=db, session=s, scenario=scenario, cast_reply_fn=_fake_reply
        )

    assert rebuilt.twist_fired is True
    assert rebuilt.pm_turn_count == 3
    # PM transcript: 3 candidate msgs + 3 cast replies + 1 twist insert = 7
    assert len(rebuilt.transcripts["pm"]) == 7
    assert len(rebuilt.transcripts["reviewer"]) == 2  # 1 candidate + 1 agent
    assert len(rebuilt.transcripts["peer"]) == 0


@pytest.mark.parametrize("channel", ["pm", "reviewer", "peer"])
async def test_handle_candidate_message_logs_actor_per_channel(channel: str) -> None:
    session = _make_active_session(role=f"Actor map {channel}")
    scenario = _build_fake_scenario(session.role)
    orch = SessionOrchestrator(scenario=scenario, cast_reply_fn=_fake_reply)

    with DbSession(engine) as db:
        s = db.get(SessionModel, session.id)
        await orch.handle_candidate_message(
            db=db, session=s, channel=channel, content="hi"
        )

    with DbSession(engine) as db:
        events = get_events(db, session.id)
    agent_events = [e for e in events if e.type == "agent_message"]
    assert len(agent_events) == 1
    # actor on the event should match the channel
    assert agent_events[0].actor.value == channel
