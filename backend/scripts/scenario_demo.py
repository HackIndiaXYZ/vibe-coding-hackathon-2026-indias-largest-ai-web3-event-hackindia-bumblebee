"""CLI: generate a single scenario and print it as JSON.

Usage (from `backend/`, with venv active):

    python scripts/scenario_demo.py
    python scripts/scenario_demo.py "Product Manager"

Useful for manually inspecting Scenario Engine output without running the
full server.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

# Allow running as `python scripts/scenario_demo.py` from backend/.
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.agents.scenario_engine import generate_scenario  # noqa: E402


async def _main() -> int:
    role = sys.argv[1] if len(sys.argv) > 1 else "Junior Full-Stack Developer"
    print(f"Generating Day One scenario for: {role}\n", file=sys.stderr)
    scenario = await generate_scenario(role)
    print(json.dumps(scenario.model_dump(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
