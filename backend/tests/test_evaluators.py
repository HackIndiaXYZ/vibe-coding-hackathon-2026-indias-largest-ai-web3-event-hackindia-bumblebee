"""Evaluator tests — evidence validator (unit) + scoring flow (integration).

The scoring-flow tests use a fake evaluator dependency so we don't pay 3
strong-tier LLM calls per test. The validator and serialization helpers
are exercised with synthetic events directly.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.agents.evaluators import (
    AxisVerdict,
    EvidenceItem,
    _events_as_json,
    validate_evidence,
)
from app.db import engine
from app.main import app, get_session_evaluator
from app.models import Actor, Event
from sqlmodel import Session as DbSession


# ===========================================================================
# Unit: evidence validator
# ===========================================================================


def _verdict(*event_ids: int) -> AxisVerdict:
    return AxisVerdict(
        axis="Judgment & Prioritization",
        score=4,
        summary="They surfaced trade-offs explicitly.",
        evidence=[
            EvidenceItem(event_id=i, ts_ms=i * 100, quote=f"e{i}", reasoning=f"r{i}")
            for i in event_ids
        ],
        flagged=False,
    )


def test_evidence_validator_keeps_real_event_ids() -> None:
    valid = {1, 2, 3, 4}
    out = validate_evidence(_verdict(1, 3), valid)
    assert out.flagged is False
    assert {e.event_id for e in out.evidence} == {1, 3}
    assert not out.summary.startswith("[FLAGGED")


def test_evidence_validator_drops_phantom_event_ids() -> None:
    valid = {1, 2, 3, 4}
    out = validate_evidence(_verdict(1, 999), valid)
    assert out.flagged is False  # one real survivor → not flagged
    assert {e.event_id for e in out.evidence} == {1}


def test_evidence_validator_flags_when_all_evidence_invalid() -> None:
    valid = {1, 2, 3}
    out = validate_evidence(_verdict(99, 100), valid)
    assert out.flagged is True
    assert out.evidence == []
    assert out.summary.startswith("[FLAGGED")


# ===========================================================================
# Unit: event log serialization (small)
# ===========================================================================


def test_events_as_json_includes_ids_and_payloads() -> None:
    events = [
        Event(id=1, session_id="s", ts_ms=0, actor=Actor.SYSTEM, type="session_created", payload={"role": "JFSD"}),
        Event(id=2, session_id="s", ts_ms=10, actor=Actor.CANDIDATE, type="candidate_message", payload={"channel": "pm", "content": "Hi"}),
    ]
    js = _events_as_json(events)
    assert '"id": 1' in js
    assert '"id": 2' in js
    assert '"candidate_message"' in js
    assert '"Hi"' in js


# ===========================================================================
# Integration: full scoring flow with a fake evaluator
# ===========================================================================


async def _fake_evaluate_session(*, events, scenario):
    """Deterministic 3-axis verdict that cites the first real event_id."""
    real_id = next((e.id for e in events if e.id is not None), 1)
    real_ts = events[0].ts_ms if events else 0
    return [
        AxisVerdict(
            axis="Judgment & Prioritization",
            score=4,
            summary="They surfaced trade-offs explicitly when the spec was vague.",
            evidence=[
                EvidenceItem(
                    event_id=real_id,
                    ts_ms=real_ts,
                    quote="(synthetic)",
                    reasoning="Cited the first event of the session.",
                )
            ],
        ),
        AxisVerdict(
            axis="Communication & Collaboration",
            score=3,
            summary="Communication was adequate; mostly used the PM channel.",
            evidence=[
                EvidenceItem(
                    event_id=real_id,
                    ts_ms=real_ts,
                    quote="(synthetic)",
                    reasoning="Used the PM channel for clarifying questions.",
                )
            ],
        ),
        AxisVerdict(
            axis="Quality of AI Use",
            score=5,
            summary="Productive AI use; questioned outputs and retained ownership.",
            evidence=[
                EvidenceItem(
                    event_id=real_id,
                    ts_ms=real_ts,
                    quote="(synthetic)",
                    reasoning="Verified each AI suggestion against the actual code.",
                )
            ],
        ),
    ]


def _override_evaluator():
    """Local override — same shape as conftest's, used by the recovery test below."""
    return _fake_evaluate_session


# The conftest already sets a global evaluator override, so most tests in
# this file don't need to manage the dependency themselves. The recovery
# test swaps in a failing evaluator temporarily then restores the global one.


def test_end_session_runs_evaluator_and_persists_scorecard() -> None:
    client = TestClient(app)
    sid = client.post("/sessions", json={"role": "Junior Full-Stack Developer"}).json()["id"]
    client.post(f"/sessions/{sid}/start")
    # Create a small event log via the routes so the evaluator has something to cite.
    client.post(
        f"/sessions/{sid}/artifact",
        json={"filename": "main.py", "content": "x = 1", "trigger": "send"},
    )

    r = client.post(f"/sessions/{sid}/end")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "complete"

    sc = client.get(f"/sessions/{sid}/scorecard")
    assert sc.status_code == 200
    payload = sc.json()
    assert payload["session_id"] == sid
    assert "decision support" in payload["disclaimer"].lower()
    axes = {a["axis"] for a in payload["axes"]}
    assert axes == {
        "Judgment & Prioritization",
        "Communication & Collaboration",
        "Quality of AI Use",
    }
    for a in payload["axes"]:
        assert 1 <= a["score"] <= 5
        assert len(a["evidence"]) >= 1
        for ev in a["evidence"]:
            assert isinstance(ev["event_id"], int)
            assert isinstance(ev["ts_ms"], int)
            assert ev["quote"]
            assert ev["reasoning"]


def test_scorecard_404_when_session_unscored() -> None:
    client = TestClient(app)
    sid = client.post("/sessions", json={"role": "Junior Full-Stack Developer"}).json()["id"]
    r = client.get(f"/sessions/{sid}/scorecard")
    assert r.status_code == 404


def test_scorecard_404_on_missing_session() -> None:
    client = TestClient(app)
    r = client.get("/sessions/nope/scorecard")
    assert r.status_code == 404


def test_end_session_409_when_already_complete() -> None:
    client = TestClient(app)
    sid = client.post("/sessions", json={"role": "Junior Full-Stack Developer"}).json()["id"]
    client.post(f"/sessions/{sid}/start")
    client.post(f"/sessions/{sid}/end")
    r = client.post(f"/sessions/{sid}/end")
    assert r.status_code == 409


async def _failing_evaluate(*, events, scenario):
    from app.agents.evaluators import ScoringError

    raise ScoringError("simulated evaluator outage")


def test_end_session_502_on_evaluator_failure_rolls_back_to_wrapping() -> None:
    """Restore retry-ability: failed scoring leaves session in WRAPPING."""
    client = TestClient(app)
    sid = client.post("/sessions", json={"role": "Junior Full-Stack Developer"}).json()["id"]
    client.post(f"/sessions/{sid}/start")

    previous_override = app.dependency_overrides.get(get_session_evaluator)
    app.dependency_overrides[get_session_evaluator] = lambda: _failing_evaluate
    try:
        r = client.post(f"/sessions/{sid}/end")
        assert r.status_code == 502
    finally:
        # Restore whatever conftest had installed.
        if previous_override is not None:
            app.dependency_overrides[get_session_evaluator] = previous_override
        else:
            app.dependency_overrides.pop(get_session_evaluator, None)

    s = client.get(f"/sessions/{sid}").json()
    assert s["status"] == "wrapping"

    # Retry succeeds with the original fake.
    r2 = client.post(f"/sessions/{sid}/end")
    assert r2.status_code == 200
    assert r2.json()["status"] == "complete"
