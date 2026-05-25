"""Settings loaded from the repo-root .env file — v3.0."""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ----- Gemini -----
    gemini_api_key: str = ""
    gemini_fast_model: str = "gemini-2.5-flash"
    # Default strong = flash too because free-tier projects typically have
    # 0-quota on gemini-2.5-pro. Thinking is enabled for strong calls (see
    # llm._wants_thinking_disabled).
    gemini_strong_model: str = "gemini-2.5-flash"

    # ----- Backend -----
    database_url: str = "sqlite:///./dayone.db"
    cors_origins: str = "http://localhost:5173"

    # ----- v3 session pacing -----
    # Default session is 60 minutes per v3 §2.2 (band 30–90 minutes).
    session_default_minutes: int = 60
    twist_trigger_turn: int = 4

    # ----- v3 evaluator ensemble -----
    # N samples per axis. 1 is free-tier-friendly (single call per axis with
    # model self-reported confidence). 3 is the real ensemble — burns 3× the
    # tokens but produces a real spread for the confidence interval and
    # agreement indicator. Tune via .env.
    evaluator_ensemble_n: int = 1

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
