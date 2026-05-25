"""Evaluator agents + evidence validator — v3.0.

v3 spec mapping:
  - Per-format rubric sets: Format A (6 axes) and Format B (5 axes).
  - 0–10 score scale (replaces v2's 1–5).
  - Each axis ships with a confidence interval (±) and qualitative band
    (Strong / Solid / Mixed / Limited / Insufficient signal), plus an
    evaluator-agreement indicator (high / medium / low / divergent).
  - Honest ensemble option: when EVALUATOR_ENSEMBLE_N > 1, runs N parallel
    samples per axis with temperature jitter and aggregates the spread into
    the real confidence interval and agreement. Single-call mode (N=1, the
    free-tier-friendly default) trusts the model's self-reported confidence.
  - Evidence validator preserved (drops phantom citations; flag if all fail).

The framing remains: decision support for a human reviewer — never a verdict.
"""
from __future__ import annotations

import asyncio
import json
import statistics
from typing import Any, Iterable

from pydantic import BaseModel, Field

from app.agents.prompts import (
    EVALUATOR_SYSTEM_TEMPLATE,
    EVALUATOR_USER_TEMPLATE,
    FORMAT_A_AI_USE_RUBRIC,
    FORMAT_A_COMMS_RUBRIC,
    FORMAT_A_JUDGMENT_RUBRIC,
    FORMAT_A_RESPONSE_TO_CHANGE_RUBRIC,
    FORMAT_A_SCOPE_RUBRIC,
    FORMAT_A_TECHNICAL_RUBRIC,
    FORMAT_B_CODE_QUALITY_RUBRIC,
    FORMAT_B_DECOMPOSITION_RUBRIC,
    FORMAT_B_TECHNICAL_RUBRIC,
    FORMAT_B_TESTING_RUBRIC,
    FORMAT_B_TIME_MGMT_RUBRIC,
)
from app.agents.scenario_engine import Scenario
from app.agents.task_engine import TaskSet
from app.config import settings
from app.llm import LLMError, Message, complete_json
from app.models import Event, SessionFormat


# ============================================================================
# Per-axis evaluator response shape (v3)
# ============================================================================


class EvidenceItem(BaseModel):
    event_id: int = Field(..., description="The integer id of a real event in the session log.")
    ts_ms: int = Field(..., description="ms-since-session-start of the cited event.")
    quote: str = Field(..., max_length=2000)
    reasoning: str = Field(..., max_length=800)


class AxisVerdict(BaseModel):
    """One axis result. Single-call mode = the model self-reports
    confidence + agreement. Ensemble mode = aggregated across samples.
    """

    axis: str
    score_0_10: float = Field(..., ge=0.0, le=10.0)
    confidence_pm: float = Field(..., ge=0.0, le=5.0)
    agreement: str = Field(..., pattern="^(high|medium|low|divergent)$")
    summary: str = Field(..., max_length=600)
    evidence: list[EvidenceItem] = Field(default_factory=list, max_length=8)
    flagged: bool = Field(default=False)

    @property
    def band(self) -> str:
        return band_for(self.score_0_10)


# Cap event-log JSON sent to the evaluator.
MAX_EVENT_LOG_CHARS = 60_000


# ============================================================================
# Score → qualitative band (deterministic, per §4.4 / Appendix C)
# ============================================================================


def band_for(score: float) -> str:
    if score >= 8.0:
        return "Strong"
    if score >= 6.5:
        return "Solid"
    if score >= 4.5:
        return "Mixed"
    if score >= 2.5:
        return "Limited"
    return "Insufficient signal"


def agreement_for_sd(sd: float) -> str:
    """Ensemble standard deviation → categorical agreement."""
    if sd <= 0.5:
        return "high"
    if sd <= 1.0:
        return "medium"
    if sd <= 1.5:
        return "low"
    return "divergent"


# ============================================================================
# Per-format axis sets
# ============================================================================


FORMAT_A_AXES: tuple[tuple[str, str], ...] = (
    ("Judgment Under Ambiguity", FORMAT_A_JUDGMENT_RUBRIC),
    ("Stakeholder Communication", FORMAT_A_COMMS_RUBRIC),
    ("Response to Unexpected Change", FORMAT_A_RESPONSE_TO_CHANGE_RUBRIC),
    ("Quality of AI Use", FORMAT_A_AI_USE_RUBRIC),
    ("Scope and Priority Management", FORMAT_A_SCOPE_RUBRIC),
    ("Technical Execution", FORMAT_A_TECHNICAL_RUBRIC),
)

FORMAT_B_AXES: tuple[tuple[str, str], ...] = (
    ("Technical Execution", FORMAT_B_TECHNICAL_RUBRIC),
    ("Problem Decomposition and Approach", FORMAT_B_DECOMPOSITION_RUBRIC),
    ("Code Quality", FORMAT_B_CODE_QUALITY_RUBRIC),
    ("Testing Discipline", FORMAT_B_TESTING_RUBRIC),
    ("Time Management Across Tasks", FORMAT_B_TIME_MGMT_RUBRIC),
)


def axes_for(fmt: SessionFormat) -> tuple[tuple[str, str], ...]:
    return FORMAT_A_AXES if fmt == SessionFormat.A else FORMAT_B_AXES


# ============================================================================
# Event-log serialization for the evaluator prompt
# ============================================================================


def _serialize_event(e: Event) -> dict:
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
        head = serialized[0:1]
        tail: list[dict] = []
        for ev in reversed(serialized):
            blob_try = json.dumps(head + tail + [ev], ensure_ascii=False, indent=1)
            if len(blob_try) > MAX_EVENT_LOG_CHARS:
                break
            tail.insert(0, ev)
        elided = len(serialized) - 1 - len(tail)
        return (
            json.dumps(head, ensure_ascii=False, indent=1)[:-1]
            + f', "...{elided} events elided...",\n'
            + json.dumps(tail, ensure_ascii=False, indent=1)[1:]
        )
    return blob


def _scenario_summary_a(scenario: Scenario) -> str:
    cast_summary = "\n".join(
        f"  - {ch}: {p.name} ({p.role}) — agenda: {p.hidden_agenda}"
        for ch, p in (
            ("pm", scenario.cast.pm),
            ("reviewer", scenario.cast.reviewer),
            ("peer", scenario.cast.peer),
        )
    )
    tasks_summary = "\n".join(f"  - [{t.id}] {t.title}" for t in scenario.tasks)
    return (
        f"Company: {scenario.company_name}\n"
        f"  {scenario.company_context}\n"
        f"Role: {scenario.role}\n"
        f"Cast:\n{cast_summary}\n"
        f"Tasks:\n{tasks_summary}\n"
        f"Planned twist (already-fired or pending): {scenario.twist.summary}\n"
        f"\nSTARTER ARTIFACT (the candidate OPENED this; they did NOT author it):\n"
        f"```\n{scenario.starter_artifact}\n```"
    )


def _scenario_summary_b(task_set: TaskSet) -> str:
    tasks_block = []
    for t in task_set.tasks:
        tasks_block.append(
            f"  - [{t.id}] {t.title} (~{t.expected_minutes}m)\n"
            f"      Description: {t.description}\n"
            f"      Hidden test categories (EVAL-ONLY): {t.hidden_tests_description}\n"
            f"      Visible tests:\n```\n{t.visible_tests}\n```\n"
            f"      Starter code (the candidate OPENED this; they did NOT author it):\n```\n{t.starter_code}\n```"
        )
    return (
        f"Company: {task_set.company_name}\n"
        f"  {task_set.company_context}\n"
        f"Role: {task_set.role}\n"
        f"\nTasks:\n" + "\n".join(tasks_block)
        + f"\n\nEvaluator notes (EVAL-ONLY): {task_set.evaluator_notes}\n"
    )


def scenario_summary_for(
    fmt: SessionFormat, scenario_obj: Scenario | TaskSet
) -> str:
    if fmt == SessionFormat.A:
        return _scenario_summary_a(scenario_obj)  # type: ignore[arg-type]
    return _scenario_summary_b(scenario_obj)  # type: ignore[arg-type]


# ============================================================================
# One-axis evaluator (single sample)
# ============================================================================


async def _evaluate_axis_once(
    *,
    axis_name: str,
    rubric: str,
    fmt: SessionFormat,
    scenario_summary: str,
    events_json: str,
    temperature: float,
) -> AxisVerdict:
    system = EVALUATOR_SYSTEM_TEMPLATE.format(
        axis_name=axis_name,
        rubric=rubric,
        format_label="A — Multi-Agent Simulation"
        if fmt == SessionFormat.A
        else "B — Solo Technical Assessment",
    )
    user = EVALUATOR_USER_TEMPLATE.format(
        scenario_summary=scenario_summary,
        events_json=events_json,
    )
    messages: list[Message] = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    raw = await complete_json(
        messages=messages,
        tier="strong",
        schema=AxisVerdict,
        temperature=temperature,
        max_output_tokens=6144,
    )
    verdict = AxisVerdict.model_validate(raw)
    verdict.axis = axis_name
    return verdict


# ============================================================================
# Ensemble per axis (N samples, aggregated)
# ============================================================================


async def evaluate_axis(
    *,
    axis_name: str,
    rubric: str,
    fmt: SessionFormat,
    scenario_summary: str,
    events_json: str,
    ensemble_n: int,
) -> AxisVerdict:
    """Run the per-axis evaluator either once (N=1) or as an N-sample ensemble.

    Ensemble strategy: independent temperature-jittered samples. Numerical
    score becomes the mean; confidence_pm becomes the half-width of the 95%
    interval (1.96 * stderr, floor 0.3); agreement is derived from the spread.
    Summary + evidence come from the median-score sample (the "median juror").
    """
    if ensemble_n <= 1:
        return await _evaluate_axis_once(
            axis_name=axis_name,
            rubric=rubric,
            fmt=fmt,
            scenario_summary=scenario_summary,
            events_json=events_json,
            temperature=0.2,
        )

    temps = _temperatures_for(ensemble_n)
    samples = await asyncio.gather(
        *(
            _evaluate_axis_once(
                axis_name=axis_name,
                rubric=rubric,
                fmt=fmt,
                scenario_summary=scenario_summary,
                events_json=events_json,
                temperature=t,
            )
            for t in temps
        ),
        return_exceptions=True,
    )
    ok: list[AxisVerdict] = [s for s in samples if isinstance(s, AxisVerdict)]
    if not ok:
        # Re-raise the first exception so the orchestrator marks the axis failed.
        first = next(s for s in samples if isinstance(s, BaseException))
        raise first

    scores = [s.score_0_10 for s in ok]
    mean = statistics.fmean(scores)
    sd = statistics.pstdev(scores) if len(scores) > 1 else 0.0
    # 95% CI half-width assuming sample stdev; clamp floor so we never claim
    # zero uncertainty on a 3-sample average.
    pm = max(0.3, 1.96 * (sd / max(1, (len(scores) - 1) ** 0.5)))

    # Pick the median-score sample for the human-readable narrative.
    median_sample = sorted(ok, key=lambda s: s.score_0_10)[len(ok) // 2]

    return AxisVerdict(
        axis=axis_name,
        score_0_10=round(mean, 1),
        confidence_pm=round(pm, 1),
        agreement=agreement_for_sd(sd),
        summary=median_sample.summary,
        evidence=median_sample.evidence,
        flagged=median_sample.flagged,
    )


def _temperatures_for(n: int) -> list[float]:
    """Spread sampling temperatures around 0.2 for ensemble diversity."""
    if n == 2:
        return [0.15, 0.4]
    if n == 3:
        return [0.1, 0.3, 0.5]
    return [0.1 + i * (0.5 / max(1, n - 1)) for i in range(n)]


# ============================================================================
# Evidence validator (drops phantom citations)
# ============================================================================


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
        summary = f"Evaluator could not cite any real events. {summary}"
    return AxisVerdict(
        axis=verdict.axis,
        score_0_10=verdict.score_0_10,
        confidence_pm=verdict.confidence_pm,
        agreement=verdict.agreement,
        summary=summary,
        evidence=surviving or [],
        flagged=flagged,
    )


def _humanize_evaluator_error(axis_name: str, err: BaseException) -> str:
    from pydantic import ValidationError

    if isinstance(err, ValidationError):
        reason = "the evaluator returned a malformed response"
    elif "429" in str(err) or "RESOURCE_EXHAUSTED" in str(err):
        reason = "the LLM quota / rate limit was hit"
    elif "503" in str(err) or "UNAVAILABLE" in str(err):
        reason = "the LLM service was temporarily unavailable"
    elif "ScoringError" in type(err).__name__:
        reason = str(err)
    else:
        reason = type(err).__name__
    return (
        f"This axis could not be scored because {reason}. "
        f"Other axes may still be usable; re-run scoring to retry."
    )


# ============================================================================
# Session-level orchestration
# ============================================================================


class ScoringError(RuntimeError):
    """Raised when one or more evaluators fail outright."""


async def evaluate_session(
    *,
    events: list[Event],
    scenario_obj: Scenario | TaskSet,
    fmt: SessionFormat,
    ensemble_n: int | None = None,
) -> list[AxisVerdict]:
    """Run all axes in parallel; validate evidence on each.

    ensemble_n defaults to settings.evaluator_ensemble_n (1 in free-tier
    config). Bump it via env to invoke the real multi-sample ensemble.
    """
    if not events:
        raise ScoringError("Cannot score an empty event log.")

    n = ensemble_n if ensemble_n is not None else settings.evaluator_ensemble_n
    valid_ids = {e.id for e in events if e.id is not None}
    axes = axes_for(fmt)
    scenario_summary = scenario_summary_for(fmt, scenario_obj)
    events_json = _events_as_json(events)

    coros = [
        evaluate_axis(
            axis_name=name,
            rubric=rubric,
            fmt=fmt,
            scenario_summary=scenario_summary,
            events_json=events_json,
            ensemble_n=n,
        )
        for name, rubric in axes
    ]
    results = await asyncio.gather(*coros, return_exceptions=True)

    verdicts: list[AxisVerdict] = []
    failed: list[tuple[str, BaseException]] = []
    for (axis_name, _), result in zip(axes, results):
        if isinstance(result, BaseException):
            failed.append((axis_name, result))
            continue
        verdicts.append(validate_evidence(result, valid_ids))

    if failed and not verdicts:
        raise ScoringError(
            "All evaluators failed: "
            + "; ".join(f"{name}: {type(e).__name__}" for name, e in failed)
        )
    if failed:
        for axis_name, err in failed:
            verdicts.append(
                AxisVerdict(
                    axis=axis_name,
                    score_0_10=5.0,  # neutral placeholder; the flagged banner explains
                    confidence_pm=2.0,
                    agreement="low",
                    summary=_humanize_evaluator_error(axis_name, err),
                    evidence=[],
                    flagged=True,
                )
            )
    return verdicts
