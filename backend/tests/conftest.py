"""Shared pytest fixtures.

We point the backend at an isolated SQLite file for tests so the dev DB
stays untouched. The env var is set BEFORE app imports so pydantic-settings
picks it up.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

# IMPORTANT: must happen before any `from app...` import so settings() reads it.
_TEST_DIR = Path(tempfile.mkdtemp(prefix="dayone-test-"))
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DIR / 'test.db'}"

import pytest  # noqa: E402
from sqlmodel import SQLModel  # noqa: E402

from app.db import engine  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    """Recreate all tables before every test for full isolation."""
    SQLModel.metadata.drop_all(engine)
    SQLModel.metadata.create_all(engine)
    yield
