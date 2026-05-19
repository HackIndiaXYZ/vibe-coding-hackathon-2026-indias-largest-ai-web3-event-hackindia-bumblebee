# Day One

> Don't interview people. Watch them work.

**Day One** replaces the broken job interview with an AI-run **work simulation**. A candidate is dropped into a fictional company for ~20–30 minutes, does realistic work while a cast of AI agents (their PM, a reviewer, a teammate) react in real time, and leaves with an **evidence-linked scorecard** of how they actually think and work.

The thesis: in an AI-saturated world you cannot reliably *detect* whether someone is faking competence. So Day One doesn't try. Using AI inside the simulation is **allowed and expected** — there is even a built-in AI assistant. What gets measured is the one thing AI cannot fake for a candidate in a live, branching, multi-stakeholder scenario: **judgment under ambiguity.**

Built for HackIndia 2026.

---

## Architecture (one-glance)

```
Scenario Engine (strong-tier LLM, structured JSON)
        │
        ▼  pre-generated fictional company + role + tasks + planned twist
┌──────────────────────────────────────────────────┐
│ Session Orchestrator (per-session state machine) │
│   routes candidate msgs by channel               │
│   injects the twist on schedule                  │
│   logs every event to telemetry                  │
└──────────────────────────────────────────────────┘
        │            ▲                ▲
   WS / REST      cast agents     work surface +
                  PM / Reviewer    AI assistant
                  / Teammate       (every query logged)
                  (fast tier)
        │
        ▼  on Finish
3 Evaluator agents (parallel, strong-tier, structured)
  → Judgment & Prioritization
  → Communication & Collaboration
  → Quality of AI Use
  → every score cites real, timestamped event evidence

→  Evidence Scorecard  (decision support, not a verdict)
```

**Key design choices:** channel-based routing (no LLM router), orchestrator-triggered twist (not agent-decided, so the demo is reliable), mandatory evidence on every score (validated; un-cited scores are rejected).

---

## Stack

| Layer    | Tech                                                          |
|----------|---------------------------------------------------------------|
| Backend  | Python 3.11+, FastAPI, SQLModel (SQLite), asyncio, WebSockets |
| Frontend | React 19 + Vite + TypeScript, Tailwind v4, Monaco editor      |
| LLM      | Gemini (Flash for cast chatter, Pro for engine + evaluators)  |
| Storage  | SQLite (zero-config local file)                               |

`backend/app/llm.py` exposes a provider-agnostic `complete(messages, tier)` so the provider can be swapped behind one config change.

---

## Run it

### 0. One-time setup

```bash
# clone / cd into the repo, then:
cp .env.example .env
# Edit .env and paste your Gemini API key (https://aistudio.google.com/apikey)
```

### 1. Backend

```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS / Linux:
# source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Health check: <http://localhost:8000/health>

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>.

---

## Repo layout

```
day-one/
├── backend/                        FastAPI app, agents, orchestrator
│   ├── app/
│   │   ├── main.py                 REST routes + WS endpoint
│   │   ├── config.py               env-loaded settings
│   │   ├── db.py                   SQLite engine + session
│   │   ├── models.py               Session, Event, Scorecard (SQLModel)
│   │   ├── schemas.py              Pydantic I/O models
│   │   ├── llm.py                  provider-agnostic LLM client
│   │   ├── telemetry.py            event-logging helpers
│   │   ├── orchestrator.py         per-session state machine + WS routing
│   │   └── agents/
│   │       ├── scenario_engine.py  generates fictional company + tasks + twist
│   │       ├── cast.py             PM / Reviewer / Teammate persona agents
│   │       ├── evaluators.py       3 evaluators + evidence validator
│   │       └── prompts.py          all prompt templates
│   └── tests/
└── frontend/
    └── src/
        ├── screens/                RoleSelect, Briefing, Workspace, Scorecard
        ├── components/             ChatChannel, WorkSurface, AIAssistantPanel, …
        ├── api/                    REST + WS clients
        ├── state/                  session store
        └── styles/tokens.css       ALL colors / spacing / fonts (re-skin point)
```

To re-skin the UI: edit `frontend/src/styles/tokens.css`. Component logic is design-token-driven and shouldn't need to change.

---

## Definition of done (demo loop)

1. User picks a role → coherent fictional scenario is generated.
2. Briefing screen shows the company, role, and task.
3. In the workspace, messaging `#pm` and `#reviewer` returns in-character, context-aware replies.
4. The twist fires mid-session as a natural `#pm` requirement change.
5. The candidate can edit code in the work surface and use the in-app AI assistant.
6. The whole session is captured as a coherent, timestamped telemetry log.
7. On *Finish*, three evaluators produce a scorecard where **every score cites a real, timestamped moment** from the session.
8. The scorecard is scannable; evidence traces back to the exact event.
9. The whole loop runs in ≤ ~30 minutes of candidate time and the demo is reliable.

---

## License

See [LICENSE](./LICENSE).
