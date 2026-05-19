"""Evaluator agents + evidence validator.

Implemented in Phase 5 — 3 evaluators run in parallel on session end, each
returning structured JSON {score, summary, evidence[]} where every evidence
item references a real telemetry event. The validator rejects un-cited scores.
"""
from __future__ import annotations

# Implemented in Phase 5.
