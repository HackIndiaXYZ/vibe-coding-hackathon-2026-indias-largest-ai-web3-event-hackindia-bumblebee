"""Cast agents — PM, Reviewer, Peer.

Each is a persona + hidden agenda + running transcript → fast-tier reply.
Channel-based routing happens in the orchestrator; this module just renders
one in-character reply given the scenario, channel, and conversation so far.

v3 rename: "teammate" → "peer" per §7 spec.
"""
from __future__ import annotations

from typing import Literal

from app.agents.prompts import (
    CAST_CHANNEL_CONTEXT,
    CAST_SYSTEM_TEMPLATE,
    CAST_TWIST_CONTEXT_TEMPLATE_OTHER,
    CAST_TWIST_CONTEXT_TEMPLATE_PM,
)
from app.agents.scenario_engine import Scenario
from app.llm import Message, complete

Channel = Literal["pm", "reviewer", "peer"]


def _build_system(scenario: Scenario, channel: Channel, twist_fired: bool) -> str:
    persona = getattr(scenario.cast, channel)
    tasks_summary = "\n".join(
        f"- [{t.id}] {t.title}: {t.description}" for t in scenario.tasks
    )
    twist_context = ""
    if twist_fired:
        tpl = (
            CAST_TWIST_CONTEXT_TEMPLATE_PM
            if channel == "pm"
            else CAST_TWIST_CONTEXT_TEMPLATE_OTHER
        )
        twist_context = tpl.format(summary=scenario.twist.summary)
    return CAST_SYSTEM_TEMPLATE.format(
        name=persona.name,
        role=persona.role,
        company_name=scenario.company_name,
        company_context=scenario.company_context,
        candidate_role_summary_brief=scenario.role,
        style=persona.style,
        hidden_agenda=persona.hidden_agenda,
        tasks_summary=tasks_summary,
        channel_context=CAST_CHANNEL_CONTEXT[channel],
        twist_context=twist_context,
    )


async def cast_reply(
    *,
    scenario: Scenario,
    channel: Channel,
    transcript: list[Message],
    twist_fired: bool = False,
) -> str:
    """Generate one in-character reply for `channel` given the running transcript."""
    system = _build_system(scenario, channel, twist_fired)
    messages: list[Message] = [{"role": "system", "content": system}]
    messages.extend(transcript)
    reply = await complete(
        messages=messages,
        tier="fast",
        temperature=0.85,
        max_output_tokens=400,
    )
    return reply.strip()
