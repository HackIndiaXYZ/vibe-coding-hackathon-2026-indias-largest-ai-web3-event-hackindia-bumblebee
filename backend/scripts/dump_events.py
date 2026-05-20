"""CLI: print a session's full event log as a readable timeline.

Useful for confirming the event log reads as a coherent, timestamped story
before evaluators ever run on it. Phase 4 acceptance criterion.

Usage (from `backend/`, with venv active):

    python scripts/dump_events.py                    # picks the most recent session
    python scripts/dump_events.py <session_id>       # specific session
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from sqlmodel import Session as DbSession, select  # noqa: E402

from app.db import engine  # noqa: E402
from app.models import Event, Session as SessionModel  # noqa: E402


_TYPE_GLYPH = {
    "session_created": "🆕",
    "scenario_loaded": "📜",
    "session_start": "▶️ ",
    "session_end": "⏹️ ",
    "candidate_message": "→ ",
    "agent_message": "← ",
    "requirement_change": "⚡",
    "artifact_snapshot": "💾",
    "ai_assistant_query": "🤖→",
    "ai_assistant_response": "🤖←",
    "ai_assistant_error": "⚠️ ",
    "scenario_generation_failed": "✗ ",
}


def _fmt_ts(ms: int) -> str:
    s, ms_r = divmod(ms, 1000)
    m, s = divmod(s, 60)
    return f"{m:02d}:{s:02d}.{ms_r:03d}"


def _short(text: str, n: int = 100) -> str:
    text = text.replace("\n", " ⏎ ")
    return text if len(text) <= n else text[: n - 1] + "…"


def main() -> int:
    target_id: str | None = sys.argv[1] if len(sys.argv) > 1 else None

    with DbSession(engine) as db:
        if target_id is None:
            session = db.exec(
                select(SessionModel).order_by(SessionModel.created_at.desc())
            ).first()
            if session is None:
                print("No sessions found in the DB.")
                return 1
            target_id = session.id
        else:
            session = db.get(SessionModel, target_id)
            if session is None:
                print(f"Session {target_id} not found.")
                return 1

        events = list(
            db.exec(
                select(Event)
                .where(Event.session_id == target_id)
                .order_by(Event.ts_ms, Event.id)
            )
        )

    print(f"Session: {session.id}   role: {session.role}   status: {session.status.value}")
    if session.scenario_json:
        company = session.scenario_json.get("company_name", "?")
        print(f"Scenario: {company}")
    print(f"Events: {len(events)}\n")

    for e in events:
        glyph = _TYPE_GLYPH.get(e.type, "·")
        ts = _fmt_ts(e.ts_ms)
        actor = e.actor.value if hasattr(e.actor, "value") else e.actor
        payload = e.payload or {}

        if e.type in ("candidate_message", "agent_message", "requirement_change"):
            channel = payload.get("channel", "")
            actor_name = payload.get("actor_name", "")
            who = f"{actor_name} #{channel}" if actor_name else f"#{channel}"
            print(f"  {ts} {glyph} [{who:25}] {_short(payload.get('content', ''))}")
        elif e.type == "artifact_snapshot":
            print(
                f"  {ts} {glyph} [{payload.get('filename','?'):25}] "
                f"{len(payload.get('content',''))}B  trigger={payload.get('trigger','?')}"
            )
        elif e.type == "ai_assistant_query":
            print(f"  {ts} {glyph} [candidate -> assistant   ] {_short(payload.get('content', ''))}")
        elif e.type == "ai_assistant_response":
            print(f"  {ts} {glyph} [assistant -> candidate   ] {_short(payload.get('content', ''))}")
        elif e.type == "scenario_loaded":
            print(
                f"  {ts} {glyph} [{actor:25}] company={payload.get('company_name','?')!r} "
                f"tasks={payload.get('task_count','?')} "
                f"twist_after={payload.get('twist_trigger_turn','?')}"
            )
        else:
            extras = json.dumps(payload, ensure_ascii=False) if payload else ""
            print(f"  {ts} {glyph} [{actor:25}] {e.type}  {_short(extras)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
