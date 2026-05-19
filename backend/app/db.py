"""SQLite engine + session dependency for FastAPI routes."""
from __future__ import annotations

from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

# SQLite needs check_same_thread=False to share the connection across the
# FastAPI worker thread pool. echo=False keeps test output clean.
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
    echo=False,
)


def init_db() -> None:
    """Create all tables. Idempotent — safe to call at every startup."""
    # Importing models registers them with SQLModel.metadata before create_all.
    from app import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a transactional DB session."""
    with Session(engine) as session:
        yield session
