"""Provider-agnostic LLM client.

Phase 1 will implement:
    async def complete(messages: list[Message], tier: Literal["fast", "strong"], **kw) -> str

Backed by Gemini today. Swappable via a single config change.
"""
from __future__ import annotations

# Implemented in Phase 1.
