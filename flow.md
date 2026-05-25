# Day One — User Flow

The candidate's journey through the product, screen by screen, including what
the backend does behind each click. Read this top-to-bottom for a complete
mental model, or jump to any section.

---

## Contents

1. [Bird's-eye flow](#1-birds-eye-flow)
2. [Screen-by-screen walkthrough](#2-screen-by-screen-walkthrough)
3. [Session state machine](#3-session-state-machine)
4. [WebSocket protocol](#4-websocket-protocol)
5. [What gets logged (telemetry events)](#5-what-gets-logged-telemetry-events)
6. [Branches: twist, retries, errors](#6-branches-twist-retries-errors)

---

## 1. Bird's-eye flow

The whole loop, end to end:

```
 ┌──────────────────┐
 │  1. Role Select  │   user picks a role
 │     screen       │
 └────────┬─────────┘
          │  click "Junior Full-Stack Developer"
          │  → POST /sessions (creates session + generates scenario,
          │                    one strong-tier Gemini call ~10–25s)
          ▼
 ┌──────────────────┐
 │   2. Briefing    │   read the fictional company, role, tasks, team
 │     screen       │
 └────────┬─────────┘
          │  click "Start your day"
          │  → POST /sessions/{id}/start  (status → ACTIVE)
          ▼
 ┌────────────────────────────────────────────────────────────────────┐
 │  3. Workspace screen                                                │
 │  ┌──────────────┬──────────────────────┬───────────────────────┐   │
 │  │              │                      │                       │   │
 │  │  channels +  │  Monaco code editor  │   AI Assistant panel  │   │
 │  │  chat thread │                      │                       │   │
 │  │              │                      │                       │   │
 │  └──────────────┴──────────────────────┴───────────────────────┘   │
 │                                                                     │
 │  WebSocket open to /sessions/{id}/ws                               │
 │  Candidate:                                                        │
 │   - sends chat to #pm / #reviewer / #teammate (WS frames)          │
 │   - edits code in Monaco (debounced POST /artifact every ~2.5s)    │
 │   - asks the AI Assistant (POST /assistant)                        │
 │  Backend:                                                          │
 │   - cast agents reply (typing → agent_message frames)              │
 │   - on PM turn N, fires the scripted twist (requirement_change)    │
 │   - logs every interaction to the event table                      │
 └────────┬───────────────────────────────────────────────────────────┘
          │  click "Finish"
          │  → POST /sessions/{id}/end
          │  → 3 evaluators run in parallel on the event log (~20–30s)
          │  → Scorecard rows persisted; session status → COMPLETE
          ▼
 ┌──────────────────┐
 │   4. Scorecard   │   GET /sessions/{id}/scorecard
 │     screen       │   three rubric axes, each with cited evidence
 └──────────────────┘
```

Total candidate time: **20–25 minutes**.
Total LLM calls: **scenario gen × 1, cast replies × N, assistant turns × M, evaluators × 3.**

---

## 2. Screen-by-screen walkthrough

### Screen 1 — Role Select  *(route: `/`)*

```
┌──────────────────────────────────────────────────────────┐
│                                                          │
│                     Day One                              │
│         Don't interview people. Watch them work.         │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │ Role                                               │  │
│  │ Junior Full-Stack Developer                        │  │
│  │ First day at a small B2B SaaS startup. One Python  │  │
│  │ API endpoint, an under-specified spec, and a PM    │  │
│  │ who'll change their mind.                          │  │
│  └────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────┐  │
│  │ Product Manager       Coming soon.                 │  │ (greyed)
│  └────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────┐  │
│  │ Data Analyst          Coming soon.                 │  │ (greyed)
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  AI use during the session is allowed.                   │
│  We measure judgment, not memorization.                  │
└──────────────────────────────────────────────────────────┘
```

**What the user does:** clicks the active role card.

**What happens:**
1. Frontend calls `POST /api/sessions` with `{role}`.
2. Backend creates a `session` row (status `created`), logs a
   `session_created` event.
3. Backend invokes the Scenario Engine — one strong-tier Gemini call
   (~10–25s). The card spinner shows "generating scenario…".
4. Backend stores the validated `Scenario` JSON on the session, logs a
   `scenario_loaded` event, transitions status to `BRIEFING`.
5. Frontend navigates to `/briefing/{sessionId}`.

**Failure mode:** Gemini error → 502 in the UI footer. (See [§6](#6-branches-twist-retries-errors).)

---

### Screen 2 — Briefing  *(route: `/briefing/{sessionId}`)*

```
┌──────────────────────────────────────────────────────────┐
│  BRIEFING                                                │
│                                                          │
│  LinkFlow                                                │
│  LinkFlow provides a unified API and dashboard for B2B   │
│  companies to manage their internal SaaS integrations…   │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │ YOUR ROLE                                          │  │
│  │ Junior Full-Stack Developer                        │  │
│  │ You've joined LinkFlow as a Junior Full-Stack…     │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  TODAY'S TASKS                                           │
│  1. Add `last_sync_timestamp` to Integration Status API  │
│     Our customers need to see when their integrations…   │
│  2. Validate Integration Status Updates                  │
│     Currently, the `status` field for an integration…    │
│  3. Update API Documentation                             │
│     Ensure the OpenAPI documentation for the…            │
│                                                          │
│  YOUR TEAM                                               │
│  ┌──────────┬──────────┬──────────┐                      │
│  │ #pm      │ #reviewer│ #teammate│                      │
│  │ Anya S.  │ Marcus T.│ Chloe L. │                      │
│  │ PM       │ Sr Eng   │ SWE      │                      │
│  └──────────┴──────────┴──────────┘                      │
│                                                          │
│                  [ Start your day → ]                    │
└──────────────────────────────────────────────────────────┘
```

**What the user does:** reads the brief, clicks **Start your day**.

**What happens:**
1. Frontend calls `POST /api/sessions/{id}/start`.
2. Backend stamps `started_at = now`, transitions status to `ACTIVE`, logs
   a `session_start` event.
3. Frontend navigates to `/workspace/{sessionId}`. The session timer
   starts counting down from 25:00 (per `SESSION_MAX_SECONDS`).

> Hidden agendas live on the backend `Scenario` and are NEVER shown to the
> candidate. The cast prompts inject them so the agents' behavior reflects
> them — the candidate must infer them from how the cast acts.

---

### Screen 3 — Workspace  *(route: `/workspace/{sessionId}`)*

```
┌─────────────────────────────────────────────────────────────────────┐
│  ▸ LinkFlow · 3 tasks    ● open    ────────    24:43      [Finish] │  ← top bar
├──────────────────┬─────────────────────────────┬───────────────────┤
│ Channels         │ 📄 main.py        snapshot  │ 🤖 AI Assistant   │
│                  │                             │ Yours to use.     │
│ # pm   ● Anya S. │ from enum import Enum       │ Every turn logged.│
│   Hey, quick…    │ from typing import Dict… ▍  │                   │
│                  │ ...                         │ ┌───────────────┐ │
│ # reviewer       │ MOCK_DB = { ... }           │ │ you           │ │
│   Marcus T.      │                             │ │ How do I…     │ │
│                  │ class IntegrationStatusEnum │ └───────────────┘ │
│ # teammate       │ ...                         │ ┌───────────────┐ │
│   Chloe L.       │                             │ │ assistant     │ │
│                  │ @app.get("/api/integrations…│ │ Use Pydantic… │ │
│ ┌──── #pm ────┐  │ async def get_integration_  │ └───────────────┘ │
│ │ Anya S. · 1:23│ status(integration_id: str):│                   │
│ │ Sure! The…    │ ...                         │ ┌───────────────┐ │
│ │              │                              │ │ Ask the…      │ │
│ │ → you  1:30  │                              │ │ ⌘/Ctrl + Enter│ │
│ │ Should the…  │                              │ │       [ Ask ] │ │
│ │              │                              │ └───────────────┘ │
│ │ [ ⚡ Anya ]   │                              │                   │
│ │ Hey quick…    │                              │                   │
│ │              │                              │                   │
│ │ [ message…  ][Send]                         │                   │
│ └─────────────┘  │                             │                   │
└──────────────────┴─────────────────────────────┴───────────────────┘
```

The three columns are the spine of the demo.

#### Top bar

- **Task brief popover** (collapsible) — click the company name to expand
  the task list inline.
- **WebSocket status** badge — green `● open` is the happy path.
- **Timer** — counts down from 25:00; turns amber under 60s, red at 0.
- **Finish button** — ends the session and kicks off scoring.

#### Left rail — channels + chat

- Three channels: `#pm`, `#reviewer`, `#teammate`. Each shows the persona
  name and an unread badge if there are new messages in an inactive channel.
- The active channel's thread renders below.
- **Three message kinds**:
  1. **Candidate message** — right-aligned, accent-bordered bubble.
  2. **Agent message** — left-aligned with actor name + relative timestamp.
  3. **Requirement change** — full-width, amber-accented "⚡" callout. The
     twist arrives like this.
- **Typing indicator** — three pulsing dots appear while the cast agent is
  generating a reply.
- **Input** — type, hit Enter or Send. Disabled if WS is closed or session
  isn't `ACTIVE`.

What the user does here:

- Asks clarifying questions in `#pm` ("should the timestamp be Unix or ISO?")
- Asks the senior engineer for technical critique in `#reviewer`
- Asks the peer about institutional gotchas in `#teammate`

What the backend does:

- For every candidate message, sends `typing: true` immediately, then runs
  one fast-tier Gemini call against the channel's persona + transcript,
  then sends the reply and `typing: false`.
- Counts PM-channel turns. When the count hits `scenario.twist.trigger_after_turn`,
  fires the scripted twist as a separate `requirement_change` frame
  ~1.2s after the normal reply. Each event lands in the telemetry log.

#### Center column — Monaco work surface

- Loaded with `scenario.starter_artifact` on session start (a fictional
  Python file with intentional landmines).
- Every change debounces 2.5s; on settle, the frontend POSTs an
  `artifact_snapshot` with `trigger=debounce`. There's also a manual
  "snapshot" link if the user wants an explicit checkpoint.
- All snapshots end up in the event table. The evaluators see how the
  code evolved during the session.

#### Right column — AI Assistant

- Visually distinct from the cast channels (different surface tone, robot
  glyph, "Yours to use. Every turn is logged." subtitle). The intent: make
  it obvious that AI use is allowed and expected — not contraband.
- Each question POSTs to `/sessions/{id}/assistant`. The backend
  reconstructs the prior assistant transcript + latest artifact snapshot
  from the event log, calls the assistant, and logs both query and
  response.
- The assistant prompt explicitly tells it not to make decisions for the
  candidate. It can verify, scaffold, explore edges. It won't pick which
  approach to use — that's the candidate's call (and the rubric measures
  exactly that).

#### Clicking Finish

1. Frontend confirms with the user.
2. Posts a final `artifact_snapshot` with `trigger=send`.
3. Closes the WebSocket.
4. POSTs `POST /api/sessions/{id}/end`.
5. Backend transitions `ACTIVE → WRAPPING (session_end event)
   → SCORING`.
6. Backend runs three evaluators in parallel — one per rubric axis —
   each given the full event log. Each returns a structured JSON verdict
   with cited evidence.
7. Backend validates evidence (drops phantom event_ids; flags verdicts
   with zero surviving citations), persists Scorecard rows, logs
   `scoring_complete`, transitions to `COMPLETE`.
8. Frontend navigates to `/scorecard/{sessionId}`.

> **Failure during scoring:** session rolls back to `WRAPPING` so the
> frontend can retry Finish. No data lost.

---

### Screen 4 — Scorecard  *(route: `/scorecard/{sessionId}`)*

```
┌──────────────────────────────────────────────────────────┐
│  SESSION RESULT                                          │
│  Scorecard                                               │
│  Decision support for a human reviewer — not an          │
│  automated verdict. Each score cites timestamped         │
│  moments from this session; review the evidence          │
│  yourself.                                               │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │ Judgment & Prioritization                  4 / 5   │  │
│  │                                                    │  │
│  │ In this session they surfaced trade-offs           │  │
│  │ explicitly when the PM expanded scope mid-flight.  │  │
│  │                                                    │  │
│  │ ▾ EVIDENCE (3)                                     │  │
│  │   ┌──────────────────────────────────────────────┐ │  │
│  │   │ @ 4:32                          event #19    │ │  │
│  │   │ "Hold on — that adds two new fields and      │ │  │
│  │   │  changes the contract for clients already    │ │  │
│  │   │  integrating. Can we ship the original next  │ │  │
│  │   │  week and the expanded shape after?"         │ │  │
│  │   │ The candidate pushed back on the requirement │ │  │
│  │   │ change rather than complying silently,       │ │  │
│  │   │ framing the cost in concrete terms.          │ │  │
│  │   └──────────────────────────────────────────────┘ │  │
│  │   ┌──────────────────────────────────────────────┐ │  │
│  │   │ @ 6:08                          event #27    │ │  │
│  │   │ "If we want both shapes to coexist…"         │ │  │
│  │   │ …                                            │ │  │
│  │   └──────────────────────────────────────────────┘ │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │ Communication & Collaboration              3 / 5   │  │
│  │ …                                                  │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │ Quality of AI Use                          5 / 5   │  │
│  │ …                                                  │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  session abc1234567…              ← Run another          │
└──────────────────────────────────────────────────────────┘
```

**What the user does:** reads the disclaimer, reviews each axis, expands
evidence blocks to see the exact quoted moments and reasoning.

**What's visible per axis:**
- Axis name
- Score 1–5 (color-tonal: red 1–2, neutral 3, green 4–5)
- 2–3 sentence summary
- Expandable evidence list — each item shows the relative timestamp, the
  event id (so the reviewer can cross-reference the raw log), a verbatim
  quote, and the evaluator's reasoning.
- A **flagged** banner if the validator dropped all citations (rare but
  possible — surfaces the problem rather than hiding it).

**Click "← Run another"** → resets the store and returns to Role Select.

---

## 3. Session state machine

The backend enforces this state machine on the `session` row:

```
        POST /sessions               POST /sessions/{id}/start
            │                                │
            ▼                                ▼
       ┌────────┐  scenario_loaded   ┌──────────┐                ┌────────┐
       │CREATED ├───────────────────▶│ BRIEFING ├───────────────▶│ ACTIVE │
       └────────┘                    └──────────┘                └───┬────┘
                                                                    │ POST /sessions/{id}/end
                                                                    ▼
                                                              ┌──────────┐
                                                              │ WRAPPING │ ← retry from here
                                                              └────┬─────┘    on scorer failure
                                                                   │ enter scoring
                                                                   ▼
                                                              ┌──────────┐
                                                              │ SCORING  │ ← 3 parallel evaluators
                                                              └────┬─────┘    + evidence validator
                                                                   │ scoring_complete
                                                                   ▼
                                                              ┌──────────┐
                                                              │ COMPLETE │ ← scorecard available
                                                              └──────────┘
```

Status invariants:
- POST `/end` is **only** legal from `ACTIVE` or `WRAPPING`. From
  `COMPLETE` it returns 409. From `SCORING` you'd race with the in-flight
  evaluator (we don't currently expose this race; SCORING is a transient
  in-process state).
- On scorer exception, the route catches it, **rolls back to WRAPPING**,
  logs a `scoring_failed` event, and returns 502. Re-posting `/end` retries
  scoring without losing the original `session_end` or `ended_at`.
- WebSocket connect is legal at any status as long as the scenario is
  present, but candidate messages are only **useful** during `ACTIVE` (the
  frontend grays out the input otherwise).

---

## 4. WebSocket protocol

URL: `ws://localhost:8000/sessions/{id}/ws`
(Vite dev proxies `/ws/...` → `ws://localhost:8000/...`.)

### Server → Client frames

```jsonc
// On connect — replays channel history from the event log.
{
  "type": "ready",
  "history": {
    "pm":       [/* prior ChatMessage[] */],
    "reviewer": [/* … */],
    "teammate": [/* … */]
  }
}

// Sent immediately when the server starts generating a reply.
{ "type": "typing", "channel": "pm", "is_typing": true }

// The cast agent's reply.
{
  "type": "agent_message",
  "channel": "pm",
  "actor_name": "Anya Sharma",
  "content": "Sure — here's the deal …",
  "ts_ms": 84120          // ms since session.started_at
}

// Then typing off.
{ "type": "typing", "channel": "pm", "is_typing": false }

// On the PM turn that hits the trigger threshold — arrives ~1.2s AFTER
// the normal agent_message, with its own ts_ms so the timeline stays in
// order.
{
  "type": "requirement_change",
  "channel": "pm",
  "actor_name": "Anya Sharma",
  "content": "Hey team, quick update — sales just promised …",
  "summary": "Field shape changed from flat to nested.",
  "ts_ms": 85500
}

// Anything that goes wrong (unknown channel, empty message, etc.)
{ "type": "error", "message": "Unknown channel: 'xyz'" }
```

### Client → Server frames

```jsonc
// The only frame the client sends.
{
  "type": "candidate_message",
  "channel": "pm",          // or "reviewer" / "teammate"
  "content": "Hey, quick question on the timestamp field…"
}
```

### Reconnect behavior

If the WebSocket drops mid-session, refreshing the page reconnects. The
orchestrator rebuilds its state from the event log (`from_event_log()`),
so the per-channel transcripts, the PM turn counter, and the
twist-fired flag are all reconstructed. **Nothing is lost** — the
in-process state is just a cache of the persisted event log.

---

## 5. What gets logged (telemetry events)

Every meaningful action lands as a row in the `event` table. This is the
substrate Phase 5 evaluators read. Types you'll see in order during one
session:

| Type | Actor | Payload | Phase |
|---|---|---|---|
| `session_created` | `system` | `{role}` | start |
| `scenario_loaded` | `system` | `{company_name, task_count, twist_trigger_turn}` | start |
| `session_start` | `system` | `{}` | on /start |
| `candidate_message` | `candidate` | `{channel, content}` | during chat |
| `agent_message` | `pm/reviewer/teammate` | `{channel, content, actor_name}` | during chat |
| `requirement_change` | `pm` | `{channel, content, actor_name, summary}` | once, on twist |
| `artifact_snapshot` | `candidate` | `{filename, content, trigger}` | every ~2.5s while editing |
| `ai_assistant_query` | `candidate` | `{content}` | per assistant turn |
| `ai_assistant_response` | `ai_assistant` | `{content}` | per assistant turn |
| `session_end` | `system` | `{}` | on /end |
| `scoring_complete` | `system` | `{axes: [...]}` | on success |
| `scoring_failed` | `system` | `{error}` | on evaluator failure |

Inspect the timeline with `python backend/scripts/dump_events.py`.

---

## 6. Branches: twist, retries, errors

### The twist

The twist is **orchestrator-triggered**, not agent-decided. This is
deliberate — it makes the demo reliable.

```
PM turn 1 ─► normal reply
PM turn 2 ─► normal reply
PM turn 3 ─► normal reply  ──┐ trigger_after_turn = 3
                              │
                              ├─► +1.2s ──► requirement_change frame
                              │             with the pre-generated twist
                              ▼
PM turn 4 ─► normal reply (now post-twist; agent system prompt
                              acknowledges the change)
```

- The threshold is `scenario.twist.trigger_after_turn`, set by the
  Scenario Engine per session (range 3–6).
- The PM-turn counter only counts candidate messages in `#pm`. Reviewer
  and teammate messages don't move the needle.
- Once fired, `twist_fired = true` is set; the twist never re-fires in
  the same session.
- The frontend auto-switches the active channel to `#pm` so the candidate
  can't miss it.

### Retry on scorer failure

```
/end ─► WRAPPING ─► SCORING ─► (one or more evaluators throw)
                                  │
                                  ▼
                       roll back to WRAPPING
                       + scoring_failed event
                       + 502 to the frontend
                                  │
                       user clicks Finish again
                                  ▼
                              SCORING (retry) ─► COMPLETE
```

`ended_at` is stamped on the FIRST `/end` call only — retries don't move
it. Idempotent in the way that matters.

### Common error surfaces (and where they appear)

| Error | When | Where the user sees it |
|---|---|---|
| Gemini 429 (quota) | Scenario gen on Briefing OR Finish on scoring | 502 in the UI footer / Finish button |
| Gemini 5xx (transient) | Any call | LLM client retries up to 3× with backoff; usually invisible |
| WebSocket disconnect | Network blip during chat | Top-bar badge turns amber → red. Refresh to reconnect; state rebuilds |
| Assistant call fails | Right rail "Ask" | `lastError` shows in the top bar; the failed query still logs as `ai_assistant_query` |
| Snapshot upload fails | Monaco debounce | Soft `lastError` in top bar; candidate keeps editing |
| Phantom evidence | Evaluator cites non-existent event_ids | Validator drops them. If ALL citations were phantoms, the axis renders with an amber ⚠ "Flagged" banner instead of silent fabrication |

---

That's the whole flow. For setup instructions, see [SETUP.md](./SETUP.md).
For the product pitch and architecture, see [README.md](./README.md).
