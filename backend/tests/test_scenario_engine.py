"""Live integration test for the Scenario Engine.

Skipped when GEMINI_API_KEY is unset / placeholder so the suite stays green
offline. When run with a real key, this exercises the full strong-tier
round-trip including JSON schema validation.
"""
from __future__ import annotations

import pytest

from app.agents.scenario_engine import Scenario, generate_scenario
from app.config import settings


def _has_real_key() -> bool:
    k = settings.gemini_api_key
    return bool(k) and not k.startswith("PASTE") and k != "your_gemini_api_key_here"


@pytest.mark.live
@pytest.mark.skipif(not _has_real_key(), reason="GEMINI_API_KEY not configured")
async def test_generate_scenario_returns_validated_shape() -> None:
    scenario = await generate_scenario("Junior Full-Stack Developer")

    assert isinstance(scenario, Scenario)
    assert scenario.role == "Junior Full-Stack Developer"

    # company & role context
    assert scenario.company_name.strip(), "company_name should be non-empty"
    assert scenario.company_context.strip(), "company_context should be non-empty"
    assert scenario.candidate_role_summary.strip()

    # cast: all three personas with hidden agendas
    for actor_name in ("pm", "reviewer", "teammate"):
        persona = getattr(scenario.cast, actor_name)
        assert persona.name.strip(), f"{actor_name} should have a name"
        assert persona.hidden_agenda.strip(), f"{actor_name} needs a hidden_agenda"

    # tasks
    assert 3 <= len(scenario.tasks) <= 4
    for t in scenario.tasks:
        assert t.id.strip() and t.title.strip() and t.description.strip()

    # starter artifact is non-trivial python-ish content
    assert len(scenario.starter_artifact) > 50

    # twist
    assert 2 <= scenario.twist.trigger_after_turn <= 8
    assert scenario.twist.pm_message.strip()
    assert scenario.twist.summary.strip()
