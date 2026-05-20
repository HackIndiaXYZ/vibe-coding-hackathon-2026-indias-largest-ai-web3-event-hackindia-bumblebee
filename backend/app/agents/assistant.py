"""In-app AI assistant.

A normal helpful coding assistant. The candidate's queries (and the responses)
are logged as `ai_assistant_query` / `ai_assistant_response` events, feeding
the "Quality of AI Use" rubric axis in Phase 5.

Multi-turn: when called repeatedly within a session, the assistant sees the
running query/response transcript so it can reference prior turns. The
candidate's latest artifact snapshot is injected as system context so the
assistant grounds answers in the actual code they're editing.
"""
from __future__ import annotations

from app.agents.prompts import ASSISTANT_SYSTEM_TEMPLATE
from app.agents.scenario_engine import Scenario
from app.llm import Message, complete

# Cap how much of the artifact we send (it can grow if the candidate pastes a
# lot). Generous but bounded so a runaway file doesn't blow the context.
MAX_ARTIFACT_CHARS = 8000


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n\n# … (truncated; {len(text) - limit} chars elided)"


async def assistant_reply(
    *,
    scenario: Scenario,
    latest_artifact: str | None,
    transcript: list[Message],
    query: str,
) -> str:
    """Generate an assistant reply.

    Args:
        scenario: active session scenario (for task context).
        latest_artifact: the most recent artifact snapshot content, or None.
        transcript: prior assistant turns as [{"role": "user"|"assistant", "content": str}, ...].
        query: the candidate's new prompt.
    """
    tasks_summary = "\n".join(
        f"- [{t.id}] {t.title}: {t.description}" for t in scenario.tasks
    )
    artifact_block = (
        _truncate(latest_artifact, MAX_ARTIFACT_CHARS)
        if latest_artifact
        else "(no work yet — the candidate hasn't snapshotted any code)"
    )
    system = ASSISTANT_SYSTEM_TEMPLATE.format(
        role=scenario.role,
        company_name=scenario.company_name,
        tasks_summary=tasks_summary,
        latest_artifact=artifact_block,
    )

    messages: list[Message] = [{"role": "system", "content": system}]
    messages.extend(transcript)
    messages.append({"role": "user", "content": query})

    reply = await complete(
        messages=messages,
        tier="fast",
        temperature=0.4,  # accurate over creative
        max_output_tokens=1200,
    )
    return reply.strip()
