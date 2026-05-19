"""Event-logging helpers.

Every interesting thing that happens during a session lands here as a row in
the `event` table. Evaluators in Phase 5 read the full log to score the
candidate, so this is the spine of the product.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Session as DbSession, select

from app.models import Actor, Event, Session


def _as_utc(dt: datetime) -> datetime:
    """Treat naive datetimes as UTC; convert tz-aware ones to UTC.

    SQLite stores datetimes as ISO strings and loses tz info on read, so
    `session.started_at` comes back naive after a round-trip. Normalize.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def log_event(
    db: DbSession,
    *,
    session: Session,
    actor: Actor,
    type: str,
    payload: dict | None = None,
) -> Event:
    """Append a telemetry event.

    `ts_ms` is computed relative to `session.started_at` so the evaluator
    timeline is consistent regardless of wall-clock skew. Pre-start events
    (e.g. scenario_loaded) land at ts_ms=0.
    """
    now = datetime.now(timezone.utc)
    started = _as_utc(session.started_at) if session.started_at else None
    ts_ms = 0 if started is None else int((now - started).total_seconds() * 1000)

    event = Event(
        session_id=session.id,
        ts_ms=ts_ms,
        ts_abs=now,
        actor=actor,
        type=type,
        payload=payload or {},
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def get_events(db: DbSession, session_id: str) -> list[Event]:
    """Fetch the full session event log, ordered by ts_ms then id."""
    statement = (
        select(Event)
        .where(Event.session_id == session_id)
        .order_by(Event.ts_ms, Event.id)
    )
    return list(db.exec(statement))
