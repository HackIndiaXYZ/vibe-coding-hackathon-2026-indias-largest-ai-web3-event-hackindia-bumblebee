"""Live WebSocket smoke script — proves the orchestrator works end-to-end.

Prerequisites:
    1. Backend running:    uvicorn app.main:app --reload --port 8000
    2. .env has a real GEMINI_API_KEY

What it does:
    - Creates a session via POST /sessions (triggers live scenario generation)
    - Starts the session
    - Opens the WS, sends candidate messages in #pm until the twist fires
    - Sends one message in #reviewer to confirm the reviewer reacts to the change
    - Prints every WS frame received

Usage (from `backend/`, with venv active):

    python scripts/ws_smoke.py
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import httpx
import websockets

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

API_BASE = "http://localhost:8000"
WS_BASE = "ws://localhost:8000"
ROLE = "Junior Full-Stack Developer"
MAX_PM_TURNS = 6


def _short(text: str, n: int = 120) -> str:
    text = text.replace("\n", " ")
    return text if len(text) <= n else text[: n - 1] + "…"


async def _consume_until_idle(ws, *, timeout: float = 6.0) -> list[dict]:
    """Pull frames until the typing indicator turns off + any follow-ups settle."""
    frames: list[dict] = []
    seen_typing_off = False
    seen_message_after_off = False
    while True:
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
        except asyncio.TimeoutError:
            return frames
        frame = json.loads(raw)
        frames.append(frame)
        t = frame.get("type")
        if t == "typing" and not frame.get("is_typing"):
            seen_typing_off = True
        elif seen_typing_off and t in ("agent_message", "requirement_change"):
            seen_message_after_off = True
        # Once we've seen typing off AND a message after it, keep listening briefly
        # for a possible follow-up requirement_change (it arrives with a small delay).
        if seen_message_after_off:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
                frames.append(json.loads(raw))
            except asyncio.TimeoutError:
                return frames
            # If there's STILL another frame coming, loop on; otherwise next timeout
            # exits the loop above.


def _print_frame(frame: dict) -> None:
    t = frame.get("type")
    if t == "ready":
        print("◯ ready")
    elif t == "typing":
        state = "…typing" if frame.get("is_typing") else "  done "
        print(f"  {state} #{frame.get('channel')}")
    elif t == "agent_message":
        print(
            f"  ← #{frame['channel']} {frame.get('actor_name', '?')}: "
            f"{_short(frame['content'])}"
        )
    elif t == "requirement_change":
        print(
            f"  ⚡ REQ CHANGE #{frame['channel']} {frame.get('actor_name','PM')}: "
            f"{_short(frame['content'])}"
        )
        print(f"        (summary: {frame['summary']})")
    elif t == "error":
        print(f"  ✗ error: {frame.get('message')}")
    else:
        print(f"  ? {frame}")


async def _send(ws, channel: str, content: str) -> None:
    print(f"  → #{channel}: {_short(content)}")
    await ws.send(
        json.dumps({"type": "candidate_message", "channel": channel, "content": content})
    )


async def _main() -> int:
    async with httpx.AsyncClient(base_url=API_BASE, timeout=120) as http:
        print(f"POST /sessions  (role={ROLE!r}) — generating scenario, may take ~10–25s…")
        r = await http.post("/sessions", json={"role": ROLE})
        r.raise_for_status()
        body = r.json()
        sid = body["id"]
        scenario = body["scenario"]
        print(
            f"  session={sid}  company={scenario['company_name']!r}  "
            f"twist_trigger_after_turn={scenario['twist']['trigger_after_turn']}"
        )
        print(f"  PM = {scenario['cast']['pm']['name']} ({scenario['cast']['pm']['role']})")

        r = await http.post(f"/sessions/{sid}/start")
        r.raise_for_status()
        print(f"POST /sessions/{sid}/start  → {r.json()['status']}")

    uri = f"{WS_BASE}/sessions/{sid}/ws"
    print(f"WS connect {uri}")
    async with websockets.connect(uri) as ws:
        ready = json.loads(await ws.recv())
        _print_frame(ready)

        twist_seen = False
        for turn in range(1, MAX_PM_TURNS + 1):
            await _send(
                ws,
                "pm",
                f"Quick question on task {turn}: how strict is the spec on the response shape?",
            )
            frames = await _consume_until_idle(ws)
            for f in frames:
                _print_frame(f)
            if any(f.get("type") == "requirement_change" for f in frames):
                twist_seen = True
                break

        if not twist_seen:
            print("⚠ twist did not fire within MAX_PM_TURNS — scenario may have a high trigger.")
        else:
            print("✓ twist fired — sending a reviewer message to probe pushback…")
            await _send(
                ws,
                "reviewer",
                "PM just changed the data shape mid-flight. How should I handle the model migration?",
            )
            for f in await _consume_until_idle(ws):
                _print_frame(f)

    print("\nDone. Open the database (backend/dayone.db) to inspect the full event log.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
