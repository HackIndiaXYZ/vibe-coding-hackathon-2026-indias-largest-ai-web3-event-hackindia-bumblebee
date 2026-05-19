"""Settings loaded from the repo-root .env file."""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root holds the single .env file (one source of truth for both backend & devops).
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
    gemini_strong_model: str = "gemini-2.5-pro"

    # ----- Backend -----
    database_url: str = "sqlite:///./dayone.db"
    cors_origins: str = "http://localhost:5173"

    # ----- Session pacing -----
    twist_trigger_turn: int = 4
    session_max_seconds: int = 1800

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
