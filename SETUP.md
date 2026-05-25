# Day One — Setup, Run & Demo Guide

End-to-end instructions for everything a human needs to do by hand: get the
code running, plug in API keys, inspect the database, run the demo for
judges, and recover when things break.

---

## Table of contents

1. [Prerequisites](#1-prerequisites)
2. [One-time setup](#2-one-time-setup)
3. [Running the app](#3-running-the-app)
4. [The database](#4-the-database)
5. [Environment variables (`.env` reference)](#5-environment-variables-env-reference)
6. [Demo script for judges](#6-demo-script-for-judges)
7. [CLI tools](#7-cli-tools)
8. [Tests](#8-tests)
9. [Troubleshooting](#9-troubleshooting)
10. [Common operations](#10-common-operations)
11. [Repo map (where stuff lives)](#11-repo-map-where-stuff-lives)

---

## 1. Prerequisites

Install these on your machine first.

| Tool | Minimum | How to verify |
|---|---|---|
| Python | 3.11+ | `python --version` |
| Node.js | 20+ (we tested on 24) | `node --version` |
| npm | 10+ | `npm --version` |
| Git | any recent | `git --version` |

A Google account (for the Gemini API key in step 2.2). No card required for
the free tier; you'll just have a 20 request / day cap. Enabling billing
lifts the cap if you plan to demo more than a few times.

> Optional: a SQLite browser (e.g. <https://sqlitebrowser.org/>) is handy
> for inspecting the event log visually, but the included CLI works fine.

---

## 2. One-time setup

### 2.1 Get the code

If you haven't already:

```powershell
git clone <repo-url> day-one
cd day-one
```

Everything below assumes your working directory is the repo root.

### 2.2 Get a Gemini API key

1. Open **Google AI Studio** → <https://aistudio.google.com/apikey>
2. Sign in with any Google account.
3. Click **"Create API key"** → choose a project (or let it create a new one).
4. Copy the key. It starts with `AIza…` and is ~39 characters long.

> Free tier gives you **20 requests/day** for `gemini-2.5-flash` plus a
> per-minute window. One full Day One demo costs **~5 calls** (1 scenario
> generation + several cast replies + 3 evaluator calls). You can run
> roughly **3 full demos per day** on the free tier.

If you'll be demoing all day at HackIndia, **enable billing** on the project
at <https://console.cloud.google.com/billing>. Gemini is cheap (~cents per
demo); the daily cap goes away.

### 2.3 Create your local `.env`

The repo includes `.env.example` at the root. Copy it to `.env` (which is
**gitignored** — never commit your real key).

PowerShell:

```powershell
Copy-Item .env.example .env
```

macOS / Linux:

```bash
cp .env.example .env
```

Open `.env` in your editor and paste your key into the `GEMINI_API_KEY=`
line so it looks like:

```
GEMINI_API_KEY=AIzaSyDqJD7QZ0yRR5jWWa5F7jHdVslrvlzwxxo
GEMINI_FAST_MODEL=gemini-2.5-flash
GEMINI_STRONG_MODEL=gemini-2.5-flash
DATABASE_URL=sqlite:///./dayone.db
CORS_ORIGINS=http://localhost:5173
TWIST_TRIGGER_TURN=4
SESSION_MAX_SECONDS=1800
```

You're free to leave the model defaults as-is. The full meaning of each
variable is documented in [§5](#5-environment-variables-env-reference).

### 2.4 Set up the backend (one time)

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

macOS / Linux:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Verify install:

```powershell
pytest -m "not live"
```

Expected: **29 passed, 2 deselected**. The 2 deselected are live-Gemini
tests; we'll exercise those when we actually run the app.

### 2.5 Set up the frontend (one time)

```powershell
cd ../frontend
npm install
```

Verify build:

```powershell
npm run build
```

Expected: `vite build` finishes in a couple seconds, output goes to
`frontend/dist/`. (You don't need to actually use `dist/` — `npm run dev`
serves a hot-reloading version.)

You're done with one-time setup.

---

## 3. Running the app

You need **two terminals open at once**.

### Terminal A — Backend (FastAPI)

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

You should see:

```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

Sanity check in another shell (or browser):

```powershell
curl http://localhost:8000/health
# → {"status":"ok","service":"day-one","version":"0.1.0"}
```

### Terminal B — Frontend (Vite)

```powershell
cd frontend
npm run dev
```

You should see:

```
  VITE v6.x.x  ready in ... ms
  ➜  Local:   http://localhost:5173/
```

Open <http://localhost:5173> in your browser. You should see the
**Day One — Role Select** screen.

### Default URLs

| Surface | URL |
|---|---|
| Frontend | <http://localhost:5173> |
| Backend health | <http://localhost:8000/health> |
| OpenAPI docs (FastAPI auto-generated) | <http://localhost:8000/docs> |
| WebSocket (used internally) | `ws://localhost:8000/sessions/{id}/ws` |

Vite proxies `/api/*` and `/ws/*` from `5173` → `8000` so the browser sees
a single origin during dev.

### Stopping

`Ctrl+C` in each terminal.

---

## 4. The database

### What it is

**SQLite** — a single file, zero config. The schema is auto-created the
first time the backend boots (via `init_db()` in `backend/app/db.py`).

### Where it lives

```
backend/dayone.db
```

It's **gitignored**. Each developer / machine has their own. There's no
"connect" step: the file is created on first boot.

Tables (defined in `backend/app/models.py`):

| Table | What it holds |
|---|---|
| `session` | One row per candidate run (status, scenario JSON, timestamps) |
| `event` | The telemetry timeline — every chat message, snapshot, AI turn |
| `scorecard` | One row per rubric axis with score, summary, JSON evidence list |

### Inspecting the data

**Option 1 — the dump_events CLI (recommended for the demo flow):**

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python scripts/dump_events.py
```

Prints the most recent session's event timeline in a glyph-prefixed format
(useful to "tell the story" of what happened in that session). Pass a
session id to dump a specific one:

```powershell
python scripts/dump_events.py <session_id>
```

**Option 2 — the SQLite CLI:**

```powershell
sqlite3 backend/dayone.db
> .tables
> SELECT id, role, status, started_at FROM session ORDER BY created_at DESC LIMIT 5;
> SELECT type, count(*) FROM event GROUP BY type;
> .quit
```

**Option 3 — a GUI:** open `backend/dayone.db` in DB Browser for SQLite.

### Resetting

The DB has no migrations. If schema changes or you just want a fresh slate:

```powershell
# Stop the backend first, then:
Remove-Item backend\dayone.db
# Restart the backend — init_db() recreates the tables on boot.
```

On macOS / Linux: `rm backend/dayone.db`.

---

## 5. Environment variables (`.env` reference)

Every variable lives in the **repo-root `.env`**. The backend loads it via
`pydantic-settings`. Environment-variable values override `.env` if both
are set.

| Variable | Default | What it does |
|---|---|---|
| `GEMINI_API_KEY` | *(empty — required)* | Your Google AI Studio key. The backend refuses to call Gemini without one. |
| `GEMINI_FAST_MODEL` | `gemini-2.5-flash` | Model used for cast-agent chatter and the AI assistant. We disable thinking on this tier so replies are snappy. |
| `GEMINI_STRONG_MODEL` | `gemini-2.5-flash` | Model used for the Scenario Engine and Evaluators. Thinking is **on** here for better structured output. Bump to `gemini-2.5-pro` if billing is enabled and you want higher quality. |
| `DATABASE_URL` | `sqlite:///./dayone.db` | SQLAlchemy connection string. Default file is `backend/dayone.db`. Swap to Postgres later if you ever deploy. |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated list of origins allowed to call the API. |
| `TWIST_TRIGGER_TURN` | `4` | (Reserved.) The scenario engine generates a per-session trigger; this env value isn't currently read by the orchestrator but documents the intent. |
| `SESSION_MAX_SECONDS` | `1800` | Hard ceiling for the session length. The frontend countdown shows 25 min by default. |

**Never commit `.env`.** The `.gitignore` already excludes it.

---

## 6. Demo script for judges

A clean ~5-minute run-through. Read this BEFORE the demo so you can narrate
in your own words rather than reciting it.

### 6.1 Pre-flight checklist (do 5 min before judging)

1. Quota check: open <https://aistudio.google.com/usage> and confirm you
   have requests left. If not — **billing on, or use the recovery plan
   in §6.5.**
2. Both servers running: backend at `:8000`, frontend at `:5173`.
3. Refresh the browser at <http://localhost:5173> — you should see the
   role select screen with the "Don't interview people. Watch them work."
   pitch.
4. Reset the DB if you want a clean slate: `Remove-Item backend\dayone.db`
   then restart the backend.
5. Have a backup tab open at <http://localhost:8000/docs> in case you
   want to show the API surface.

### 6.2 The 60-second pitch (before clicking anything)

> Job interviews are broken because AI made it impossible to detect fakery.
> So instead of trying to catch cheaters, Day One drops a candidate into a
> simulated first day at a fictional company. They do real work — chat with
> their PM, write code, use a built-in AI assistant — while their session
> is fully logged. Three AI evaluators then produce a scorecard where every
> score cites a specific timestamped moment from what actually happened.
> The judge becomes the candidate for 5 minutes.

### 6.3 The walkthrough (step by step)

| Step | What you do | What to say |
|---|---|---|
| 1 | Click the **Junior Full-Stack Developer** card on the role-select screen. | "We're picking the dev role. The other two roles are placeholders — same engine, different surface." |
| 2 | Wait ~15–25s as the Scenario Engine runs. | "Behind the scenes, one strong-tier Gemini call is generating a fictional company, a 3-task brief, a starter code file with a deliberate landmine or two, and a planned mid-session twist." |
| 3 | On the **Briefing screen**, read out the generated company name, the role summary, and one of the task descriptions. | "Look — none of this exists. Different judges, different scenarios. The candidate can't have memorized this." |
| 4 | Click **Start your day**. | "Timer kicks off. 25-minute hard cap." |
| 5 | In the **Workspace**, point at the three columns: channels (left), Monaco code editor (center), AI assistant (right). | "Slack channels for the cast on the left, a real code editor in the middle, and a clearly-labeled AI assistant on the right. AI use is **allowed and expected** — what we measure is *quality of judgment*, not whether they used AI." |
| 6 | Click **`#pm`** in the channel list. Type a clarifying question — for example: *"Hey, quick clarification on the timestamp field — do you want it as Unix seconds or ISO 8601?"* — and hit Send. | "Real Slack-style chat. The PM has a hidden agenda the candidate has to infer from how she responds." |
| 7 | When the PM replies, narrate it. Send another message — maybe push back on scope: *"If we add validation that strictly, the existing clients will break. Should I add a deprecation period or do you want a hard cutover?"* | "Notice the PM is in character with a hidden agenda. Day One isn't checking the candidate's *answer* — it's watching *how they ask questions* and *how they handle pushback*." |
| 8 | Open the Monaco editor. Point at one of the deliberately suspect lines in the starter code (e.g., a variable computed but never used, or a hard-coded value). Make a small edit. | "Snapshots upload every couple of seconds — the evaluators see how the code evolves." |
| 9 | Click the **AI Assistant** panel. Ask something useful: *"What's the cleanest way to validate an enum value in FastAPI with Pydantic v2?"* | "Every assistant turn is logged. The 'Quality of AI Use' axis later looks at whether the candidate used AI to verify and explore, or to outsource thinking." |
| 10 | Continue chatting in `#pm` until you've sent 3–4 messages there. **The twist will fire.** A new PM message arrives with a warning-colored accent bar. Click into it. | "That's the twist — orchestrator-triggered after a fixed turn count so the demo is reliable. Notice it's a separate frame, separate styling. The candidate has to choose: comply, push back, replan, or ignore?" |
| 11 | React to the twist in `#pm`: *"Hold on — that adds two new fields and changes the contract for clients already integrating. Can we ship the original next week and the expanded shape after?"* | "Now I'm pushing back, on the record. That'll show up in the scorecard." |
| 12 | Click **`#reviewer`** and message the senior engineer about the change: *"PM just expanded scope mid-flight. How do you want me to handle the migration for existing rows?"* | "Channel-appropriate communication. PM for scope, reviewer for technical critique." |
| 13 | Click **Finish** in the top right. Confirm the modal. | "This kicks off three evaluators in parallel — strong-tier Gemini calls, each given the full event log plus its rubric. Takes ~20–30 seconds." |
| 14 | When the **Scorecard** appears, walk through each of the three axes. For each one, click an evidence item to expand. | "Each score from 1 to 5. Each score has 2-5 pieces of evidence. Each evidence item is a real quote from the session, tied to a specific timestamp." |
| 15 | Read out one quoted evidence item and tie it back to what happened: "Look — this evidence cites the moment I pushed back on the twist at 4:32. The evaluator saw it." | "Crucially: this is *decision support* for a human reviewer. It's not an automated verdict. The reviewer sees the score AND the receipts." |

### 6.4 Anticipated questions

- **"What if they just cheat with AI?"** → Cheating is irrelevant when there's no static answer. The scenario is freshly generated, the cast reacts live, the twist mutates the spec mid-session. AI inside the sim is allowed. We measure judgment.
- **"Is it deterministic enough for fair evaluation?"** → The orchestrator triggers the twist on a fixed turn count. Both candidates in the same role get comparable structural beats. The scenarios differ in surface, not in the kinds of decisions required.
- **"What's the bias story?"** → Names are invented. Roles are roles. The scorecard is evidence-cited so the human reviewer can audit every claim. We don't make hiring decisions; we surface receipts.
- **"How long to evaluate one candidate?"** → 20–25 minutes of candidate time + 30 seconds of compute for the scorecard. Reviewer reads the scorecard in 5 minutes.
- **"What about non-coding roles?"** → Same engine. Different starter artifact (doc surface instead of Monaco), different rubric. The roadmap has PM and Data Analyst stubs visible on the role select.

### 6.5 If Gemini quota is exhausted (recovery plan)

Free tier is 20 calls/day. Each demo burns ~5. If you've run out:

1. **Easiest:** wait until 12:30 PM IST tomorrow (resets at midnight Pacific).
2. **Real fix:** enable billing on the Google Cloud project for the API key. Takes 2 minutes; the daily cap vanishes. Costs cents per demo.
3. **Cold-fail demo:** open a previously-generated session via the events CLI:
   ```powershell
   python scripts/dump_events.py
   ```
   …and narrate the timeline. Less impressive but proves the loop ran.

---

## 7. CLI tools

All under `backend/scripts/`. Run from `backend/` with the venv active.

### `scenario_demo.py` — print a generated scenario

```powershell
python scripts/scenario_demo.py
# or
python scripts/scenario_demo.py "Product Manager"
```

One live strong-tier Gemini call → prints the full Scenario JSON. Good for
sanity-checking that the engine produces sensible output for a given role.

### `dump_events.py` — print a session's event timeline

```powershell
python scripts/dump_events.py                # most-recent session
python scripts/dump_events.py <session_id>   # specific session
```

Pretty-printed timeline with glyphs for each event type
(`→` candidate message, `←` agent reply, `⚡` requirement change,
`💾` artifact snapshot, `🤖→`/`🤖←` AI assistant). Use this to
prove the event log reads as a coherent story.

### `ws_smoke.py` — live WS smoke test against a running backend

```powershell
# Terminal A: backend running on :8000
# Terminal B:
python scripts/ws_smoke.py
```

Creates a session, opens the WebSocket, sends 3–6 messages to `#pm` until
the twist fires, then sends one message to `#reviewer`. Useful end-to-end
test without a browser.

---

## 8. Tests

From `backend/` with venv active.

```powershell
pytest                  # everything, including live Gemini tests
pytest -m "not live"    # offline only — safe even when quota is exhausted
pytest -v -k orchestrator  # filter by name
```

Test breakdown (31 total):

| File | Count | Live? |
|---|---|---|
| `test_health.py` | 1 | offline |
| `test_sessions.py` | 3 | offline |
| `test_artifact_and_assistant.py` | 6 | offline |
| `test_orchestrator.py` | 7 | offline |
| `test_ws.py` | 3 | offline |
| `test_evaluators.py` | 9 | offline |
| `test_llm_smoke.py` | 1 | **live** |
| `test_scenario_engine.py` | 1 | **live** |

Live tests are tagged `@pytest.mark.live`. They make real Gemini calls and
count against your daily quota.

---

## 9. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `502 Bad Gateway` on Briefing screen ("Scenario generation failed") | Gemini API issue — likely 429 daily quota | Wait for quota reset OR enable billing OR `dump_events.py` of a previous session as a fallback. |
| Briefing spins forever, no error | Backend not actually running, or CORS misconfigured | Check Terminal A for the uvicorn process; check `CORS_ORIGINS` in `.env`. |
| `502` on **Finish** | One of the 3 evaluators failed | The session rolls back to `WRAPPING`. Click Finish again to retry. |
| Top bar shows `● closed` red status | WS dropped or never connected | Refresh the page. The orchestrator state will rebuild from the event log; chat history is preserved. |
| Workspace input boxes disabled | Session not yet `ACTIVE` | Make sure you clicked "Start your day" on the Briefing screen. |
| `pytest` fails with `429 RESOURCE_EXHAUSTED` | Daily Gemini quota exhausted | Run `pytest -m "not live"` instead. |
| `pytest` fails with `LLMNotConfigured: GEMINI_API_KEY is not set` | `.env` missing or placeholder still present | Edit `.env` and paste a real key. |
| Monaco editor doesn't render | `@monaco-editor/react` install corrupted | `cd frontend && rm -rf node_modules && npm install` |
| Frontend won't compile | Type drift after editing a Pydantic model | Update the mirror in `frontend/src/types.ts`. Run `npx tsc --noEmit` to see the exact mismatch. |
| Port 8000 already in use | Another process owns it | Kill it (`netstat -ano | findstr 8000` → `taskkill /PID <pid> /F`) OR change the port: `uvicorn app.main:app --reload --port 8001` AND update Vite's `vite.config.ts` proxy. |
| Port 5173 already in use | Another Vite is running | `npm run dev -- --port 5174` |
| WebSocket reconnect loop | Backend restarted; client retries | Refresh the page once. State will rehydrate from the event log. |
| Database "table not found" | `init_db()` didn't run | Restart the backend; it runs in the FastAPI lifespan. |
| Scorecard renders with no axes | Evaluator failed silently | Check uvicorn logs; look for `scoring_failed` events in `dump_events.py`. |

---

## 10. Common operations

### Add a new role

1. In `frontend/src/screens/RoleSelect.tsx`, find the `ROLES` array and flip
   one of the placeholder cards (PM or Data Analyst) to `available: true`.
2. The Scenario Engine prompt is role-agnostic — it'll generate scenarios
   for any role string. For better defaults, edit `DEFAULT_DOMAIN_HINT` in
   `backend/app/agents/prompts.py` to suit non-dev roles.
3. (Optional) If the new role uses a different work surface (e.g., doc
   editor instead of Monaco), branch in `frontend/src/components/WorkSurface.tsx`.

### Tweak the rubrics

`backend/app/agents/prompts.py` — `JUDGMENT_RUBRIC`, `COMMS_RUBRIC`,
`AI_USE_RUBRIC`. Each is a multi-line string. Change the score-guide bullets
to retune what 3 vs 5 means. The evaluator picks it up on the next session.

### Tweak twist behavior

The twist is generated per-session by the Scenario Engine (see
`agents/scenario_engine.py` → `Twist` Pydantic model). Its `trigger_after_turn`
field is honored by the orchestrator. If you want a fixed trigger across
all sessions, override it after generation in `app/main.py`:

```python
scenario.twist.trigger_after_turn = 3
```

…right after `await gen(req.role)`.

### Re-skin the UI

**`frontend/src/styles/tokens.css`** is the only file you should need to
edit. Every color, font, radius, and layout rail width is a Tailwind v4
`@theme` variable. Change values there; components automatically pick them
up via `bg-surface`, `text-fg`, etc.

```css
@theme {
  --color-bg: #0b0c0f;       /* main background */
  --color-accent: #60a5fa;   /* primary actions */
  /* … */
}
```

### Swap LLM providers

`backend/app/llm.py` is the only file with provider-specific code. Replace
the body of `complete()` to call OpenAI / Anthropic / a sponsor API; keep
the function signature (`messages`, `tier`, `temperature`,
`max_output_tokens`, `response_schema`) intact and everything else just
works.

### Inspect the OpenAPI / poke routes

<http://localhost:8000/docs> — FastAPI's Swagger UI. Click "Try it out"
on any endpoint to fire it. Good for showing judges the API surface.

---

## 11. Repo map (where stuff lives)

```
day-one/
├── .env                            (your local key — gitignored)
├── .env.example                    (template; commit-safe)
├── README.md                       (product overview + run instructions)
├── SETUP.md                        (this file)
│
├── backend/
│   ├── pyproject.toml              (pytest config, markers)
│   ├── requirements.txt
│   ├── dayone.db                   (SQLite — created on first boot, gitignored)
│   ├── .venv/                      (gitignored)
│   ├── app/
│   │   ├── main.py                 (FastAPI routes + WebSocket endpoint)
│   │   ├── config.py               (env-loaded settings)
│   │   ├── db.py                   (SQLite engine + init)
│   │   ├── models.py               (Session / Event / Scorecard tables)
│   │   ├── schemas.py              (Pydantic request/response models)
│   │   ├── llm.py                  (provider-agnostic Gemini client + retry)
│   │   ├── telemetry.py            (event-logging helpers)
│   │   ├── orchestrator.py         (per-session WS state machine + twist)
│   │   └── agents/
│   │       ├── prompts.py          (ALL prompt templates + rubrics)
│   │       ├── scenario_engine.py  (generates fictional scenarios)
│   │       ├── cast.py             (PM / Reviewer / Teammate replies)
│   │       ├── assistant.py        (in-app AI assistant)
│   │       └── evaluators.py       (3 parallel evaluators + evidence validator)
│   ├── scripts/
│   │   ├── scenario_demo.py        (CLI: print a generated scenario)
│   │   ├── ws_smoke.py             (CLI: live WS end-to-end probe)
│   │   └── dump_events.py          (CLI: pretty-print a session timeline)
│   └── tests/                      (31 tests; pytest -m "not live" runs 29 offline)
│
└── frontend/
    ├── package.json
    ├── vite.config.ts              (Vite proxy: /api → :8000, /ws → :8000)
    ├── tsconfig.json
    ├── index.html
    ├── node_modules/               (gitignored)
    └── src/
        ├── main.tsx, App.tsx       (entry + routes)
        ├── types.ts                (TS mirrors of backend Pydantic shapes)
        ├── api/
        │   ├── client.ts           (REST wrappers)
        │   └── ws.ts               (WebSocket client)
        ├── state/store.ts          (Zustand store — session state machine)
        ├── screens/                (RoleSelect, Briefing, Workspace, Scorecard)
        ├── components/             (Timer, TaskBrief, ChannelList, ChatChannel,
        │                            WorkSurface, AIAssistantPanel, EvidenceItem,
        │                            ScoreAxis)
        └── styles/
            ├── global.css          (base + Tailwind import)
            └── tokens.css          (ONLY file to edit for re-skin)
```

---

## Last words

If something explodes during a demo, the recovery path is almost always:

1. **Check the top-bar WS status** (open/connecting/closed) and **the last
   error** in the workspace top bar.
2. **Refresh the page** — orchestrator state rebuilds from the event log;
   chat history is preserved.
3. **Check Terminal A** (uvicorn) for stack traces.
4. **Run `python scripts/dump_events.py`** to see what actually happened.
5. **Delete `backend/dayone.db`** and restart if you want a truly clean
   slate.

You've got this.
