"""Per-session orchestrator: routes messages, injects the twist, logs everything.

The orchestrator owns per-channel transcripts, the PM-turn counter, and the
twist-fired flag. State is fully reconstructible from the telemetry event log,
so reconnects are safe — `from_event_log()` rebuilds state from DB events.

Design decisions baked in:
- **Channel-based routing** (no LLM router). The WS client tags every message
  with its channel; the orchestrator looks up the persona and replies.
- **Orchestrator-triggered twist** (not agent-decided). When the PM-channel
  turn count reaches `scenario.twist.trigger_after_turn`, the orchestrator
  injects the scripted twist message as a SEPARATE PM ping. Reliable demo.
- **Mandatory telemetry**. Every candidate message, every agent reply, and
  the twist firing land in the event log — this is what the Phase 5
  evaluators read.
"""
from __future__ import annotations

from typing import Awaitable, Callable, Literal

from sqlmodel import Session as DbSession

from app.agents.cast import cast_reply as default_cast_reply
from app.agents.scenario_engine import Scenario
from app.models import Actor, Event, Session as SessionModel
from app.telemetry import get_events, log_event

Channel = Literal["pm", "reviewer", "teammate"]
CHANNELS: tuple[Channel, ...] = ("pm", "reviewer", "teammate")

# Hint: a callable that takes the same kwargs as cast_reply.
CastReplyFn = Callable[..., Awaitable[str]]

_CHANNEL_TO_ACTOR: dict[Channel, Actor] = {
    "pm": Actor.PM,
    "reviewer": Actor.REVIEWER,
    "teammate": Actor.TEAMMATE,
}


class TurnOutcome:
    """Result of one candidate→cast exchange.

    Attributes:
        reply: the agent's normal reply.
        reply_ts_ms: telemetry timestamp of the reply (for evidence linking).
        actor_name: the persona's display name (e.g. "Anya Sharma").
        twist: the twist payload if this turn triggered it, else None.
    """

    def __init__(
        self,
        *,
        reply: str,
        reply_ts_ms: int,
        actor_name: str,
        twist: dict | None = None,
    ) -> None:
        self.reply = reply
        self.reply_ts_ms = reply_ts_ms
        self.actor_name = actor_name
        self.twist = twist


class SessionOrchestrator:
    """In-memory state for one session. Rebuildable from the event log."""

    def __init__(
        self,
        *,
        scenario: Scenario,
        transcripts: dict[Channel, list[dict]] | None = None,
        pm_turn_count: int = 0,
        twist_fired: bool = False,
        cast_reply_fn: CastReplyFn | None = None,
    ) -> None:
        self.scenario = scenario
        self.transcripts: dict[Channel, list[dict]] = transcripts or {
            ch: [] for ch in CHANNELS
        }
        self.pm_turn_count = pm_turn_count
        self.twist_fired = twist_fired
        self._cast_reply = cast_reply_fn or default_cast_reply

    # ------------------------------------------------------------------ build

    @classmethod
    def from_event_log(
        cls,
        *,
        db: DbSession,
        session: SessionModel,
        scenario: Scenario,
        cast_reply_fn: CastReplyFn | None = None,
    ) -> "SessionOrchestrator":
        """Replay events to rebuild orchestrator state. Safe to call on every connect."""
        transcripts: dict[Channel, list[dict]] = {ch: [] for ch in CHANNELS}
        pm_turn_count = 0
        twist_fired = False

        for ev in get_events(db, session.id):
            ev_type = ev.type
            ch = ev.payload.get("channel") if ev.payload else None
            content = ev.payload.get("content", "") if ev.payload else ""

            if ev_type == "candidate_message" and ch in transcripts:
                transcripts[ch].append({"role": "user", "content": content})
                if ch == "pm":
                    pm_turn_count += 1
            elif ev_type == "agent_message" and ch in transcripts:
                transcripts[ch].append({"role": "assistant", "content": content})
            elif ev_type == "requirement_change":
                twist_fired = True
                transcripts["pm"].append({"role": "assistant", "content": content})

        return cls(
            scenario=scenario,
            transcripts=transcripts,
            pm_turn_count=pm_turn_count,
            twist_fired=twist_fired,
            cast_reply_fn=cast_reply_fn,
        )

    # ------------------------------------------------------------------ act

    async def handle_candidate_message(
        self,
        db: DbSession,
        session: SessionModel,
        channel: Channel,
        content: str,
    ) -> TurnOutcome:
        """Handle one candidate message: log, generate reply, maybe fire twist."""
        if channel not in CHANNELS:
            raise ValueError(f"Unknown channel: {channel}")

        # 1. Log + append candidate message
        log_event(
            db,
            session=session,
            actor=Actor.CANDIDATE,
            type="candidate_message",
            payload={"channel": channel, "content": content},
        )
        self.transcripts[channel].append({"role": "user", "content": content})
        if channel == "pm":
            self.pm_turn_count += 1

        # 2. Decide whether THIS turn should also fire the twist (after the reply).
        should_fire_twist = (
            not self.twist_fired
            and channel == "pm"
            and self.pm_turn_count >= self.scenario.twist.trigger_after_turn
        )

        # 3. Generate the in-character reply (twist context applied AFTER firing).
        reply = await self._cast_reply(
            scenario=self.scenario,
            channel=channel,
            transcript=self.transcripts[channel],
            twist_fired=self.twist_fired,
        )
        self.transcripts[channel].append({"role": "assistant", "content": reply})
        persona = getattr(self.scenario.cast, channel)
        reply_event = log_event(
            db,
            session=session,
            actor=_CHANNEL_TO_ACTOR[channel],
            type="agent_message",
            payload={
                "channel": channel,
                "content": reply,
                "actor_name": persona.name,
            },
        )

        twist_payload: dict | None = None
        if should_fire_twist:
            twist_msg = self.scenario.twist.pm_message
            twist_event = log_event(
                db,
                session=session,
                actor=Actor.PM,
                type="requirement_change",
                payload={
                    "channel": "pm",
                    "content": twist_msg,
                    "actor_name": self.scenario.cast.pm.name,
                    "summary": self.scenario.twist.summary,
                },
            )
            self.transcripts["pm"].append({"role": "assistant", "content": twist_msg})
            self.twist_fired = True
            twist_payload = {
                "content": twist_msg,
                "actor_name": self.scenario.cast.pm.name,
                "summary": self.scenario.twist.summary,
                "ts_ms": twist_event.ts_ms,
            }

        return TurnOutcome(
            reply=reply,
            reply_ts_ms=reply_event.ts_ms,
            actor_name=persona.name,
            twist=twist_payload,
        )


def history_for_channel(events: list[Event], channel: Channel) -> list[dict]:
    """Helper for the WS handshake: reconstruct visible chat history for a channel.

    Returns a list of message dicts: {actor, actor_name, content, ts_ms, kind}
    where kind ∈ {"candidate", "agent", "requirement_change"}.
    """
    history: list[dict] = []
    for ev in events:
        if not ev.payload:
            continue
        if ev.payload.get("channel") != channel:
            continue
        if ev.type == "candidate_message":
            history.append(
                {
                    "kind": "candidate",
                    "channel": channel,
                    "content": ev.payload.get("content", ""),
                    "ts_ms": ev.ts_ms,
                }
            )
        elif ev.type == "agent_message":
            history.append(
                {
                    "kind": "agent",
                    "channel": channel,
                    "actor_name": ev.payload.get("actor_name", ""),
                    "content": ev.payload.get("content", ""),
                    "ts_ms": ev.ts_ms,
                }
            )
        elif ev.type == "requirement_change":
            history.append(
                {
                    "kind": "requirement_change",
                    "channel": "pm",
                    "actor_name": ev.payload.get("actor_name", ""),
                    "content": ev.payload.get("content", ""),
                    "summary": ev.payload.get("summary", ""),
                    "ts_ms": ev.ts_ms,
                }
            )
    return history
