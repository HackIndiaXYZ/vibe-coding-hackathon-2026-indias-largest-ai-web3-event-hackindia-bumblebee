"""Provider-agnostic LLM client.

Exposes one async function:

    await complete(messages, tier="fast" | "strong", ...) -> str

Backed by Gemini today (google-genai). The shape is intentionally minimal so
that swapping to OpenAI / Anthropic / a sponsor SDK later is a one-file change.
Messages use a portable {"role": "system"|"user"|"assistant", "content": str}
schema and are translated to whichever provider format we're on.
"""
from __future__ import annotations

import json
from typing import Any, Literal

from google import genai
from google.genai import types

from app.config import settings

Tier = Literal["fast", "strong"]
Role = Literal["system", "user", "assistant"]
Message = dict[str, str]  # {"role": Role, "content": str}


class LLMNotConfigured(RuntimeError):
    """Raised when no API key is configured."""


class LLMError(RuntimeError):
    """Raised on a provider-side failure we want to surface up cleanly."""


_client: genai.Client | None = None


def _ensure_key() -> str:
    key = settings.gemini_api_key
    if not key or key.startswith("PASTE") or key == "your_gemini_api_key_here":
        raise LLMNotConfigured(
            "GEMINI_API_KEY is not set in .env. "
            "Get a key from https://aistudio.google.com/apikey and paste it in."
        )
    return key


def _get_client() -> genai.Client:
    global _client
    key = _ensure_key()
    if _client is None:
        _client = genai.Client(api_key=key)
    return _client


def _model_for(tier: Tier) -> str:
    return settings.gemini_fast_model if tier == "fast" else settings.gemini_strong_model


def _to_gemini_contents(messages: list[Message]) -> tuple[str | None, list[types.Content]]:
    """Split off system instructions; map remaining messages to Gemini Content.

    Gemini uses role="user" / role="model"; "system" is a separate top-level
    `system_instruction` config field. Multiple system messages are joined.
    """
    system_parts: list[str] = []
    contents: list[types.Content] = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if role == "system":
            system_parts.append(content)
            continue
        gemini_role = "model" if role == "assistant" else "user"
        contents.append(
            types.Content(role=gemini_role, parts=[types.Part.from_text(text=content)])
        )
    system = "\n\n".join(system_parts) if system_parts else None
    return system, contents


def _wants_thinking_disabled(tier: Tier, model: str) -> bool:
    """Gemini 2.5 models spend output tokens on internal thinking by default.

    For the fast tier (cast-agent chatter, AI-assistant turns) that latency
    and token cost is wasted — we want short, in-character replies. Disable
    thinking on 2.5-family fast models. The strong tier keeps thinking on,
    since the Scenario Engine and Evaluators genuinely benefit from it.
    """
    return tier == "fast" and "2.5" in model


async def complete(
    messages: list[Message],
    tier: Tier = "fast",
    *,
    temperature: float = 0.7,
    max_output_tokens: int | None = None,
    response_schema: dict[str, Any] | None = None,
) -> str:
    """Single async completion.

    Args:
        messages: Portable message list. Use role="system" for instructions.
        tier: "fast" (cast chatter) or "strong" (scenario engine + evaluators).
        temperature: 0.0 for deterministic structured output, ~0.7 for chatter.
        max_output_tokens: Optional ceiling. NOTE on Gemini 2.5: total budget
            covers both visible output AND thinking tokens, so set this with
            headroom or rely on thinking being disabled (see fast-tier rule).
        response_schema: If given, the provider will be asked for JSON matching
            this schema. The returned string is JSON text — caller parses it.

    Returns:
        The assistant's text content. Empty string if the provider returned no
        content (very rare; usually means a safety block).
    """
    client = _get_client()
    model = _model_for(tier)
    system, contents = _to_gemini_contents(messages)

    config = types.GenerateContentConfig(temperature=temperature)
    if system:
        config.system_instruction = system
    if max_output_tokens is not None:
        config.max_output_tokens = max_output_tokens
    if response_schema is not None:
        config.response_mime_type = "application/json"
        config.response_schema = response_schema
    if _wants_thinking_disabled(tier, model):
        config.thinking_config = types.ThinkingConfig(thinking_budget=0)

    try:
        response = await client.aio.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )
    except Exception as exc:  # noqa: BLE001  surface as our own error type
        raise LLMError(f"Gemini call failed: {exc}") from exc

    return response.text or ""


async def complete_json(
    messages: list[Message],
    tier: Tier = "strong",
    *,
    schema: dict[str, Any],
    temperature: float = 0.2,
    max_output_tokens: int | None = None,
) -> Any:
    """Convenience wrapper: ask for JSON and parse it.

    Used by the Scenario Engine and Evaluators where structured output is
    mandatory. Raises LLMError if the provider returns un-parseable JSON.
    """
    raw = await complete(
        messages,
        tier=tier,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
        response_schema=schema,
    )
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LLMError(f"Provider returned malformed JSON: {raw[:200]}...") from exc
