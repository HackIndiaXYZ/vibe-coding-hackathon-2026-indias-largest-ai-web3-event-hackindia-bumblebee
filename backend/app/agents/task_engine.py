"""Format B — generates a solo technical task set.

No cast. No twist. No in-session AI assistant. Just a fictional company
context, candidate framing, and 2–3 coding tasks with visible tests, hidden
test descriptions, and a starter file. Strong-tier Gemini call returning
structured JSON; retry-once on malformed output.

The persisted shape is intentionally similar to Format A's Scenario at the
top level (company_name, role, candidate_role_summary, tasks) so the
frontend Briefing screen can share most of its template. Differences:
  - Cast is absent.
  - There is no `starter_artifact` field on the task set as a whole; each
    task carries its own `starter_code`.
  - There is no twist.
"""
from __future__ import annotations

from pydantic import BaseModel, Field, ValidationError

from app.agents.prompts import TASK_SET_SYSTEM, TASK_SET_USER_TEMPLATE
from app.llm import LLMError, Message, complete_json


class CodingTask(BaseModel):
    id: str = Field(..., description="Short kebab-case slug.")
    title: str
    description: str = Field(..., description="3–5 sentence problem statement.")
    starter_code: str = Field(..., description="Python 3.11+, syntactically valid.")
    visible_tests: str = Field(..., description="pytest-style assertions, visible to candidate.")
    hidden_tests_description: str = Field(
        ...,
        description="Plain-English description of hidden-test categories. EVAL-ONLY.",
    )
    expected_minutes: int = Field(..., ge=5, le=60)


class TaskSetGenerationError(RuntimeError):
    """Raised when task-set generation fails after retries."""


class TaskSet(BaseModel):
    company_name: str
    company_context: str
    role: str
    candidate_role_summary: str = Field(..., description="2-3 sentences.")
    tasks: list[CodingTask] = Field(..., min_length=2, max_length=3)
    evaluator_notes: str = Field(
        ...,
        description="Plain-English calibration notes for the evaluator. NEVER shown to candidate.",
    )


async def generate_task_set(role: str, *, level: str = "Junior") -> TaskSet:
    """Generate a fictional Day One Format B task set for the given role."""
    messages: list[Message] = [
        {"role": "system", "content": TASK_SET_SYSTEM},
        {
            "role": "user",
            "content": TASK_SET_USER_TEMPLATE.format(role=role, level=level),
        },
    ]
    last_err: Exception | None = None
    for attempt in (1, 2):
        try:
            raw = await complete_json(
                messages=messages,
                tier="strong",
                schema=TaskSet,
                temperature=0.7,
                max_output_tokens=8192,
            )
            return TaskSet.model_validate(raw)
        except (LLMError, ValidationError, KeyError, TypeError) as exc:
            last_err = exc
            if attempt == 1:
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            "Your previous response was rejected (malformed JSON or "
                            "missing fields). Re-generate from scratch, strictly "
                            "following the schema. JSON only."
                        ),
                    }
                )

    raise TaskSetGenerationError(
        f"Task set generation failed after 2 attempts: {last_err}"
    ) from last_err
