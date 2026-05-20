"""Generates a fictional company + role + tasks + planned twist.

One strong-tier Gemini call returning structured JSON, validated against a
Pydantic schema. Retries once on malformed output; the second failure raises
so the route can surface a 502 to the frontend.
"""
from __future__ import annotations

from pydantic import BaseModel, Field, ValidationError

from app.agents.prompts import (
    DEFAULT_DOMAIN_HINT,
    SCENARIO_SYSTEM,
    SCENARIO_USER_TEMPLATE,
)
from app.llm import LLMError, Message, complete_json


# ----- response shape -----

class CastPersona(BaseModel):
    name: str = Field(..., description="Invented full name.")
    role: str = Field(..., description="Job title at the fictional company.")
    style: str = Field(..., description="One-line description of how they talk.")
    hidden_agenda: str = Field(
        ...,
        description=(
            "What this persona secretly cares about and may not say out loud. "
            "The candidate's job is to infer it from behavior."
        ),
    )


class Cast(BaseModel):
    pm: CastPersona
    reviewer: CastPersona
    teammate: CastPersona


class Task(BaseModel):
    id: str = Field(..., description="Short kebab-case slug.")
    title: str
    description: str = Field(..., description="2–3 sentences.")


class Twist(BaseModel):
    trigger_after_turn: int = Field(
        ...,
        ge=2,
        le=8,
        description="Turns of candidate->PM exchange before the twist fires.",
    )
    pm_message: str = Field(..., description="The natural-sounding PM message.")
    summary: str = Field(..., description="One sentence: what changed. For evaluators.")


class Scenario(BaseModel):
    company_name: str
    company_context: str = Field(..., description="One sentence about the company.")
    role: str = Field(..., description="Echoes the requested candidate role.")
    candidate_role_summary: str = Field(..., description="2-3 sentences.")
    cast: Cast
    tasks: list[Task] = Field(..., min_length=3, max_length=4)
    starter_artifact: str = Field(..., description="Initial Python file content.")
    twist: Twist


# ----- generator -----

class ScenarioGenerationError(RuntimeError):
    """Raised when scenario generation fails after retries."""


async def generate_scenario(
    role: str,
    *,
    domain_hint: str = DEFAULT_DOMAIN_HINT,
) -> Scenario:
    """Generate a fictional Day One scenario for the given candidate role.

    One strong-tier Gemini call. Retries ONCE on malformed JSON or validation
    failure, then raises ScenarioGenerationError.
    """
    messages: list[Message] = [
        {"role": "system", "content": SCENARIO_SYSTEM},
        {
            "role": "user",
            "content": SCENARIO_USER_TEMPLATE.format(role=role, domain_hint=domain_hint),
        },
    ]

    last_err: Exception | None = None
    for attempt in (1, 2):
        try:
            raw = await complete_json(
                messages=messages,
                tier="strong",
                schema=Scenario,
                temperature=0.85,  # we want creative, varied scenarios
                max_output_tokens=4096,
            )
            return Scenario.model_validate(raw)
        except (LLMError, ValidationError, KeyError, TypeError) as exc:
            last_err = exc
            # Append a corrective nudge for the retry attempt.
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

    raise ScenarioGenerationError(
        f"Scenario generation failed after 2 attempts: {last_err}"
    ) from last_err
