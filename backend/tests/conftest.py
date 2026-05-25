"""Shared pytest fixtures — v3.0.

Points the backend at an isolated SQLite file. Overrides the scenario
generator, task-set generator, and session evaluator dependencies with
deterministic fakes so the suite runs fully offline.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

# IMPORTANT: must happen before any `from app...` import so settings() reads it.
_TEST_DIR = Path(tempfile.mkdtemp(prefix="dayone-test-"))
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DIR / 'test.db'}"

import pytest  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402

from app.agents.evaluators import AxisVerdict, EvidenceItem  # noqa: E402
from app.agents.scenario_engine import (  # noqa: E402
    Cast,
    CastPersona,
    Scenario,
    Task,
    Twist,
)
from app.agents.task_engine import CodingTask, TaskSet  # noqa: E402
from app.db import engine  # noqa: E402
from app.main import (  # noqa: E402
    app,
    get_scenario_generator,
    get_session_evaluator,
    get_task_set_generator,
)
from app.models import SessionFormat  # noqa: E402


# ----- deterministic Format A scenario -----


def _build_fake_scenario(role: str) -> Scenario:
    persona = CastPersona(
        name="Alex Test",
        role="Test PM",
        style="terse",
        hidden_agenda="ship before Friday",
    )
    return Scenario(
        company_name="TestCo",
        company_context="A fictional B2B SaaS test fixture.",
        role=role,
        candidate_role_summary="Fix one endpoint in 60 minutes.",
        cast=Cast(
            pm=persona,
            reviewer=CastPersona(
                name="Sam Reviewer",
                role="Staff Engineer",
                style="direct",
                hidden_agenda="burnt out",
            ),
            peer=CastPersona(
                name="Jordan Peer",
                role="Engineer II",
                style="friendly",
                hidden_agenda="knows the gotcha but won't volunteer it",
            ),
        ),
        tasks=[
            Task(id="t1", title="Fix the endpoint", description="Make /x return JSON."),
            Task(id="t2", title="Add a field", description="Add created_at."),
            Task(id="t3", title="Write a test", description="One pytest case."),
        ],
        starter_artifact="# placeholder\n\ndef noop():\n    return None\n",
        twist=Twist(
            trigger_after_turn=3,
            pm_message="hey quick thing — sales promised a different shape, can you swap?",
            summary="data shape changed mid-session",
        ),
    )


async def _fake_scenario_generator(role: str) -> Scenario:
    return _build_fake_scenario(role)


def _override_scenario_generator():
    return _fake_scenario_generator


app.dependency_overrides[get_scenario_generator] = _override_scenario_generator


# ----- deterministic Format B task set -----


def _build_fake_task_set(role: str) -> TaskSet:
    return TaskSet(
        company_name="TestCo",
        company_context="A fictional B2B SaaS test fixture for solo coding.",
        role=role,
        candidate_role_summary="Three small Python tasks in ~60 minutes.",
        tasks=[
            CodingTask(
                id="sum-pair",
                title="Sum-pair",
                description="Return the unique pair that sums to target.",
                starter_code="def sum_pair(nums, target):\n    pass\n",
                visible_tests="assert sum_pair([1,2,3], 4) == (1,3)\n",
                hidden_tests_description="negative numbers, duplicates, empty",
                expected_minutes=20,
            ),
            CodingTask(
                id="rate-limit",
                title="Rate limiter",
                description="Implement a simple token-bucket rate limiter.",
                starter_code="class RateLimiter:\n    def allow(self):\n        pass\n",
                visible_tests="rl = RateLimiter(rate=2)\nassert rl.allow() is True\n",
                hidden_tests_description="time advance, burst, refill",
                expected_minutes=25,
            ),
        ],
        evaluator_notes="Excellent: O(n) sum-pair, clean RateLimiter with time injection.",
    )


async def _fake_task_set_generator(role: str, *, level: str = "Junior") -> TaskSet:
    return _build_fake_task_set(role)


def _override_task_set_generator():
    return _fake_task_set_generator


app.dependency_overrides[get_task_set_generator] = _override_task_set_generator


# ----- deterministic evaluator -----


async def _fake_evaluate_session(*, events, scenario_obj, fmt, ensemble_n=None):
    real_id = next((e.id for e in events if e.id is not None), 1)
    real_ts = events[0].ts_ms if events else 0
    sample = EvidenceItem(
        event_id=real_id,
        ts_ms=real_ts,
        quote="(synthetic conftest evidence)",
        reasoning="Cited the first event of the session as a placeholder.",
    )
    if fmt == SessionFormat.A:
        axes = [
            "Judgment Under Ambiguity",
            "Stakeholder Communication",
            "Response to Unexpected Change",
            "Quality of AI Use",
            "Scope and Priority Management",
            "Technical Execution",
        ]
    else:
        axes = [
            "Technical Execution",
            "Problem Decomposition and Approach",
            "Code Quality",
            "Testing Discipline",
            "Time Management Across Tasks",
        ]
    return [
        AxisVerdict(
            axis=name,
            score_0_10=7.0,
            confidence_pm=0.6,
            agreement="medium",
            summary="In this session they showed solid, evidence-cited work.",
            evidence=[sample],
        )
        for name in axes
    ]


def _override_evaluator():
    return _fake_evaluate_session


app.dependency_overrides[get_session_evaluator] = _override_evaluator


@pytest.fixture(autouse=True)
def fresh_db():
    """Recreate all tables before every test for full isolation."""
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    yield
