"""Evaluator agents + evidence validator.

Three evaluators run in PARALLEL on session end — one per rubric axis. Each
sees the full event log and a rubric, and returns structured JSON:

    {axis, score 1-5, summary, evidence: [{event_id, ts_ms, quote, reasoning}, ...]}

The evidence validator drops/flags any evidence item whose event_id isn't a
real event in this session's log — protects against hallucinated citations.
Output is framed as decision support for a human reviewer, never a verdict.
"""
from __future__ import annotations

import asyncio
import json
from typing import Iterable

from pydantic import BaseModel, Field

from app.agents.prompts import (
    AI_USE_RUBRIC,
    COMMS_RUBRIC,
    EVALUATOR_SYSTEM_TEMPLATE,
    EVALUATOR_USER_TEMPLATE,
    JUDGMENT_RUBRIC,
)
from app.agents.scenario_engine import Scenario
from app.llm import LLMError, Message, complete_json
from app.models import Event

# ----- response shape -----


class EvidenceItem(BaseModel):
    event_id: int = Field(..., description="The integer id of a real event in the session log.")
    ts_ms: int = Field(..., description="ms-since-session-start of the cited event.")
    quote: str = Field(..., max_length=600, description="Verbatim or near-verbatim snippet from the event payload.")
    reasoning: str = Field(..., max_length=600, description="Why this evidence supports the score.")


class AxisVerdict(BaseModel):
    axis: str
    score: int = Field(..., ge=1, le=5)
    summary: str = Field(..., max_length=600)
    # min_length is enforced by the *prompt* (Gemini is asked for 2–5 items).
    # We don't enforce it in the schema because the post-call evidence validator
    # may legitimately drop all items if they're phantoms — we want to keep
    # the verdict and mark it flagged rather than reject it.
    evidence: list[EvidenceItem] = Field(default_factory=list, max_length=8)
    flagged: bool = Field(
        default=False,
        description="True if no evidence items survived validation (citations didn't match real event_ids).",
    )


# ----- rubric axes config -----

AXES: tuple[tuple[str, str], ...] = (
    ("Judgment & Prioritization", JUDGMENT_RUBRIC),
    ("Communication & Collaboration", COMMS_RUBRIC),
    ("Quality of AI Use", AI_USE_RUBRIC),
)

# Cap the event-log JSON to keep prompt size sane. A 25-min session produces
# ~50-150 events typically; this is generous.
MAX_EVENT_LOG_CHARS = 60_000


# ----- event serialization for the evaluator prompt -----


def _serialize_event(e: Event) -> dict:
    """Compact dict representation the evaluator sees for one event."""
    return {
        "id": e.id,
        "ts_ms": e.ts_ms,
        "actor": e.actor.value if hasattr(e.actor, "value") else str(e.actor),
        "type": e.type,
        "payload": e.payload or {},
    }


def _events_as_json(events: Iterable[Event]) -> str:
    serialized = [_serialize_event(e) for e in events]
    blob = json.dumps(serialized, ensure_ascii=False, indent=1)
    if len(blob) > MAX_EVENT_LOG_CHARS:
        # Keep newest events (last in the array) — they're usually more informative.
        # Trim from the head while keeping the array brackets intact.
        head = serialized[0:1]
        tail_count = 0
        tail: list[dict] = []
        for ev in reversed(serialized):
            blob_try = json.dumps(head + tail + [ev], ensure_ascii=False, indent=1)
            if len(blob_try) > MAX_EVENT_LOG_CHARS:
                break
            tail.insert(0, ev)
            tail_count += 1
        elided = len(serialized) - 1 - tail_count
        return (
            json.dumps(head, ensure_ascii=False, indent=1)[:-1]
            + f', "...{elided} events elided...",\n'
            + json.dumps(tail, ensure_ascii=False, indent=1)[1:]
        )
    return blob


def _scenario_summary(scenario: Scenario) -> str:
    cast_summary = "\n".join(
        f"  - {ch}: {p.name} ({p.role}) — agenda: {p.hidden_agenda}"
        for ch, p in (
            ("pm", scenario.cast.pm),
            ("reviewer", scenario.cast.reviewer),
            ("teammate", scenario.cast.teammate),
        )
    )
    tasks_summary = "\n".join(f"  - [{t.id}] {t.title}" for t in scenario.tasks)
    return (
        f"Company: {scenario.company_name}\n"
        f"  {scenario.company_context}\n"
        f"Role: {scenario.role}\n"
        f"Cast:\n{cast_summary}\n"
        f"Tasks:\n{tasks_summary}\n"
        f"Planned twist (already-fired or pending): {scenario.twist.summary}"
    )


# ----- one-axis evaluator -----


async def evaluate_axis(
    *,
    axis_name: str,
    rubric: str,
    scenario: Scenario,
    events: list[Event],
) -> AxisVerdict:
    """Run one evaluator against the event log. Strong tier, structured output."""
    system = EVALUATOR_SYSTEM_TEMPLATE.format(axis_name=axis_name, rubric=rubric)
    user = EVALUATOR_USER_TEMPLATE.format(
        scenario_summary=_scenario_summary(scenario),
        events_json=_events_as_json(events),
    )
    messages: list[Message] = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    raw = await complete_json(
        messages=messages,
        tier="strong",
        schema=AxisVerdict,
        temperature=0.2,  # calibrated, not creative
        max_output_tokens=6144,
    )
    verdict = AxisVerdict.model_validate(raw)
    # The schema doesn't force the right axis label — pin it from our side.
    verdict.axis = axis_name
    return verdict


# ----- evidence validator -----


def validate_evidence(verdict: AxisVerdict, valid_event_ids: set[int]) -> AxisVerdict:
    """Drop evidence items whose event_id is not a real session event.

    If ALL evidence is dropped, return the verdict with `flagged=True` and an
    empty evidence list so the human reviewer sees the citation failure
    rather than a silently-fabricated score.
    """
    surviving = [e for e in verdict.evidence if e.event_id in valid_event_ids]
    flagged = len(surviving) == 0
    summary = verdict.summary
    if flagged:
        summary = f"[FLAGGED: evaluator cited no real events] {summary}"
    return AxisVerdict(
        axis=verdict.axis,
        score=verdict.score,
        summary=summary,
        evidence=surviving or [],  # may be empty
        flagged=flagged,
    )


# ----- session-level orchestration -----


class ScoringError(RuntimeError):
    """Raised when one or more evaluators fail outright."""


async def evaluate_session(
    *, events: list[Event], scenario: Scenario
) -> list[AxisVerdict]:
    """Run all 3 evaluators in parallel; validate evidence on each."""
    if not events:
        raise ScoringError("Cannot score an empty event log.")

    valid_ids = {e.id for e in events if e.id is not None}

    coros = [
        evaluate_axis(axis_name=name, rubric=rubric, scenario=scenario, events=events)
        for name, rubric in AXES
    ]
    results = await asyncio.gather(*coros, return_exceptions=True)

    verdicts: list[AxisVerdict] = []
    errors: list[str] = []
    for (axis_name, _), result in zip(AXES, results):
        if isinstance(result, BaseException):
            errors.append(f"{axis_name}: {result!r}")
            continue
        verdicts.append(validate_evidence(result, valid_ids))

    if errors and not verdicts:
        raise ScoringError(f"All evaluators failed: {'; '.join(errors)}")
    if errors:
        # Partial success — surface a SYSTEM-flagged axis row so the human
        # reviewer sees something failed rather than missing axes silently.
        for err_msg in errors:
            axis_name = err_msg.split(":", 1)[0]
            verdicts.append(
                AxisVerdict(
                    axis=axis_name,
                    score=3,  # neutral placeholder
                    summary=f"[FLAGGED: evaluator failed — {err_msg}]",
                    evidence=[],
                    flagged=True,
                )
            )
    return verdicts
