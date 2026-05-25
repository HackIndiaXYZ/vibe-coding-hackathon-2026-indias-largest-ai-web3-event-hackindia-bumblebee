"""Evaluator tests — v3 evidence validator + scoring flow."""
from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import Session as DbSession

from app.agents.evaluators import (
    AxisVerdict,
    EvidenceItem,
    _events_as_json,
    agreement_for_sd,
    band_for,
    validate_evidence,
)
from app.main import app, get_session_evaluator
from app.models import Actor, Event


# ===========================================================================
# Band + agreement derivation
# ===========================================================================


def test_band_for_thresholds() -> None:
    assert band_for(9.0) == "Strong"
    assert band_for(7.5) == "Solid"
    assert band_for(5.0) == "Mixed"
    assert band_for(3.0) == "Limited"
    assert band_for(1.0) == "Insufficient signal"


def test_agreement_for_sd_buckets() -> None:
    assert agreement_for_sd(0.2) == "high"
    assert agreement_for_sd(0.8) == "medium"
    assert agreement_for_sd(1.3) == "low"
    assert agreement_for_sd(2.0) == "divergent"


# ===========================================================================
# Evidence validator
# ===========================================================================


def _verdict(*event_ids: int) -> AxisVerdict:
    return AxisVerdict(
        axis="Judgment Under Ambiguity",
        score_0_10=7.0,
        confidence_pm=0.5,
        agreement="medium",
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
    assert "could not cite" in out.summary.lower()


# ===========================================================================
# Event-log serialization
# ===========================================================================


def test_events_as_json_includes_ids_and_payloads() -> None:
    events = [
        Event(
            id=1,
            session_id="s",
            ts_ms=0,
            actor=Actor.SYSTEM,
            type="session_created",
            payload={"role": "JFSD"},
        ),
        Event(
            id=2,
            session_id="s",
            ts_ms=10,
            actor=Actor.CANDIDATE,
            type="candidate_message",
            payload={"channel": "pm", "content": "Hi"},
        ),
    ]
    js = _events_as_json(events)
    assert '"id": 1' in js
    assert '"id": 2' in js
    assert '"candidate_message"' in js
    assert '"Hi"' in js


# ===========================================================================
# Full scoring flow with fake evaluator (set up in conftest)
# ===========================================================================


def test_end_session_runs_evaluator_and_persists_v3_scorecard() -> None:
    client = TestClient(app)
    sid = client.post(
        "/sessions",
        json={"role": "Junior Full-Stack Developer", "format": "A"},
    ).json()["id"]
    client.post(f"/sessions/{sid}/start")
    client.post(
        f"/sessions/{sid}/artifact",
        json={"filename": "main.py", "content": "x = 1", "trigger": "send"},
    )

    r = client.post(f"/sessions/{sid}/end")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "complete"

    sc = client.get(f"/sessions/{sid}/scorecard").json()
    assert sc["session_id"] == sid
    assert sc["format"] == "A"
    assert "decision support" in sc["disclaimer"].lower()
    axes = {a["axis"] for a in sc["axes"]}
    assert axes == {
        "Judgment Under Ambiguity",
        "Stakeholder Communication",
        "Response to Unexpected Change",
        "Quality of AI Use",
        "Scope and Priority Management",
        "Technical Execution",
    }
    for a in sc["axes"]:
        assert 0.0 <= a["score_0_10"] <= 10.0
        assert a["confidence_pm"] >= 0.0
        assert a["band"] in {
            "Strong",
            "Solid",
            "Mixed",
            "Limited",
            "Insufficient signal",
        }
        assert a["agreement"] in {"high", "medium", "low", "divergent"}
        for ev in a["evidence"]:
            assert isinstance(ev["event_id"], int)

    # Integrity context surfaced
    assert "tab_focus_lost_count" in sc["integrity"]
    assert isinstance(sc["integrity"]["notes"], list)


def test_format_b_scorecard_uses_format_b_axes() -> None:
    client = TestClient(app)
    sid = client.post(
        "/sessions",
        json={"role": "Junior Full-Stack Developer", "format": "B"},
    ).json()["id"]
    client.post(f"/sessions/{sid}/start")
    client.post(
        f"/sessions/{sid}/artifact",
        json={"filename": "sum-pair.py", "content": "def sum_pair(a,b): pass", "trigger": "send"},
    )
    client.post(f"/sessions/{sid}/end")
    sc = client.get(f"/sessions/{sid}/scorecard").json()
    axes = {a["axis"] for a in sc["axes"]}
    assert axes == {
        "Technical Execution",
        "Problem Decomposition and Approach",
        "Code Quality",
        "Testing Discipline",
        "Time Management Across Tasks",
    }


def test_scorecard_404_when_session_unscored() -> None:
    client = TestClient(app)
    sid = client.post(
        "/sessions",
        json={"role": "Junior Full-Stack Developer", "format": "A"},
    ).json()["id"]
    r = client.get(f"/sessions/{sid}/scorecard")
    assert r.status_code == 404


def test_scorecard_404_on_missing_session() -> None:
    client = TestClient(app)
    r = client.get("/sessions/nope/scorecard")
    assert r.status_code == 404


def test_end_session_409_when_already_complete() -> None:
    client = TestClient(app)
    sid = client.post(
        "/sessions",
        json={"role": "Junior Full-Stack Developer", "format": "A"},
    ).json()["id"]
    client.post(f"/sessions/{sid}/start")
    client.post(f"/sessions/{sid}/end")
    r = client.post(f"/sessions/{sid}/end")
    assert r.status_code == 409


async def _failing_evaluate(*, events, scenario_obj, fmt, ensemble_n=None):
    from app.agents.evaluators import ScoringError

    raise ScoringError("simulated evaluator outage")


def test_end_session_502_on_evaluator_failure_rolls_back_to_wrapping() -> None:
    client = TestClient(app)
    sid = client.post(
        "/sessions",
        json={"role": "Junior Full-Stack Developer", "format": "A"},
    ).json()["id"]
    client.post(f"/sessions/{sid}/start")

    previous_override = app.dependency_overrides.get(get_session_evaluator)
    app.dependency_overrides[get_session_evaluator] = lambda: _failing_evaluate
    try:
        r = client.post(f"/sessions/{sid}/end")
        assert r.status_code == 502
    finally:
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
