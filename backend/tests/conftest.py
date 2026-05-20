"""Shared pytest fixtures.

We point the backend at an isolated SQLite file for tests so the dev DB
stays untouched. The env var is set BEFORE app imports so pydantic-settings
picks it up.

We also override the scenario generator dependency with a deterministic fake
so tests are fully offline (no Gemini call required to test session routes).
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

from app.agents.scenario_engine import (  # noqa: E402
    Cast,
    CastPersona,
    Scenario,
    Task,
    Twist,
)
from app.db import engine  # noqa: E402
from app.main import app, get_scenario_generator  # noqa: E402


def _build_fake_scenario(role: str) -> Scenario:
    """A deterministic scenario used in offline tests."""
    persona = CastPersona(
        name="Alex Test",
        role="Test Role",
        style="terse",
        hidden_agenda="ship before Friday",
    )
    return Scenario(
        company_name="TestCo",
        company_context="A fictional B2B SaaS test fixture.",
        role=role,
        candidate_role_summary="Fix one endpoint in 25 minutes.",
        cast=Cast(
            pm=persona,
            reviewer=CastPersona(
                name="Sam Reviewer",
                role="Staff Engineer",
                style="direct",
                hidden_agenda="burnt out",
            ),
            teammate=CastPersona(
                name="Jordan Peer",
                role="Engineer II",
                style="friendly",
                hidden_agenda="knows the gotcha but won't volunteer it",
            ),
        ),
        tasks=[
            Task(id="t1", title="Fix the endpoint", description="Make /x return JSON."),
            Task(id="t2", title="Add a field", description="Add `created_at`."),
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


@pytest.fixture(autouse=True)
def fresh_db():
    """Recreate all tables before every test for full isolation."""
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    yield
