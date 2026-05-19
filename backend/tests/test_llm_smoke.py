"""Live LLM smoke test.

Skipped automatically if GEMINI_API_KEY is unset / still the placeholder, so
the test suite stays green in CI or before the user pastes their key.
"""
from __future__ import annotations

import pytest

from app.config import settings
from app.llm import complete


def _has_real_key() -> bool:
    k = settings.gemini_api_key
    return bool(k) and not k.startswith("PASTE") and k != "your_gemini_api_key_here"


@pytest.mark.skipif(not _has_real_key(), reason="GEMINI_API_KEY not configured")
async def test_complete_returns_text_from_gemini() -> None:
    text = await complete(
        messages=[
            {"role": "system", "content": "Respond with exactly one word, no punctuation."},
            {"role": "user", "content": "Say only the word: pong"},
        ],
        tier="fast",
        temperature=0.0,
        max_output_tokens=64,
    )
    assert isinstance(text, str)
    assert len(text.strip()) > 0
    # We don't assert exact content — providers occasionally add punctuation —
    # only that the round-trip works and we got some text back.
