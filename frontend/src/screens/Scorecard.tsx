/**
 * Screen 4 — Scorecard.
 * Header with the disclaimer (decision support, not a verdict) + one
 * ScoreAxis block per rubric axis with expandable EvidenceItems.
 */
import { useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";

import ScoreAxis from "../components/ScoreAxis";
import { useStore } from "../state/store";

export default function Scorecard() {
  const { sessionId = "" } = useParams();
  const navigate = useNavigate();
  const scorecard = useStore((s) => s.scorecard);
  const loading = useStore((s) => s.scorecardLoading);
  const error = useStore((s) => s.lastError);
  const loadScorecard = useStore((s) => s.loadScorecard);
  const loadSession = useStore((s) => s.loadSession);
  const reset = useStore((s) => s.reset);

  useEffect(() => {
    if (!sessionId) return;
    // Make sure session is in the store so subsequent loadScorecard knows the id.
    void loadSession(sessionId).then(() => loadScorecard());
  }, [sessionId, loadSession, loadScorecard]);

  return (
    <main className="min-h-screen p-8 max-w-4xl mx-auto space-y-8">
      <header className="space-y-2">
        <p className="text-xs uppercase tracking-wider text-faint">Session result</p>
        <h1 className="text-3xl font-semibold tracking-tight text-fg">Scorecard</h1>
        <p className="text-sm text-muted leading-relaxed">
          {scorecard?.disclaimer ??
            "Decision support for a human reviewer — not an automated verdict. Each score cites timestamped moments from this session; review the evidence yourself."}
        </p>
      </header>

      {loading && !scorecard && (
        <p className="text-muted text-sm">Loading scorecard…</p>
      )}
      {error && (
        <p className="text-danger text-sm" role="alert">
          {error}
        </p>
      )}

      {scorecard && (
        <section className="space-y-4" aria-label="Rubric axes">
          {scorecard.axes.map((a) => (
            <ScoreAxis key={a.axis} axis={a} />
          ))}
        </section>
      )}

      <footer className="pt-4 flex items-center justify-between text-xs text-faint">
        <p>session {sessionId}</p>
        <button
          type="button"
          onClick={() => {
            reset();
            navigate("/");
          }}
          className="text-sm text-muted hover:text-fg transition-colors"
        >
          ← Run another
        </button>
      </footer>
    </main>
  );
}
