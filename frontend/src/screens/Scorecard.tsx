/**
 * Scorecard screen — v3.
 *
 * The artifact the recruiter sees + the candidate sees, identical. Per-axis
 * 0–10 score with ± confidence interval, qualitative band, evaluator
 * agreement, and cited evidence. Integrity Context surfaced separately.
 * Right-to-explanation link + appeal CTA in the footer.
 */
import { useEffect } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import AppealForm from "../components/AppealForm";
import ComplianceFooter from "../components/ComplianceFooter";
import FormatBadge from "../components/FormatBadge";
import IntegrityContextEl from "../components/IntegrityContext";
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
    void loadSession(sessionId).then(() => loadScorecard());
  }, [sessionId, loadSession, loadScorecard]);

  return (
    <>
      <main id="main" className="max-w-4xl mx-auto px-4 py-8 space-y-8">
        <header className="space-y-3">
          <p className="text-xs uppercase tracking-wider text-faint">
            Session result
          </p>
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="text-3xl font-semibold tracking-tight text-fg">
              Scorecard
            </h1>
            {scorecard && (
              <FormatBadge
                format={scorecard.format}
                size="md"
                practice={scorecard.is_practice}
              />
            )}
          </div>
          <p className="text-sm text-muted leading-relaxed max-w-2xl">
            {scorecard?.disclaimer ??
              "Decision support for a human reviewer — not an automated verdict."}
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
          <>
            <section className="space-y-4" aria-label="Rubric axes">
              {scorecard.axes.map((a) => (
                <ScoreAxis key={a.axis} axis={a} />
              ))}
            </section>

            <IntegrityContextEl context={scorecard.integrity} format={scorecard.format} />

            <section className="grid sm:grid-cols-2 gap-3">
              <Link
                to={`/explanation/${sessionId}`}
                className="rounded-lg border border-border bg-surface p-4 hover:border-accent/50 transition-colors"
              >
                <p className="text-xs uppercase tracking-wider text-faint">
                  Right to explanation
                </p>
                <p className="text-sm text-fg mt-1">
                  Plain-language description of every axis →
                </p>
              </Link>
              <Link
                to="/rights"
                className="rounded-lg border border-border bg-surface p-4 hover:border-accent/50 transition-colors"
              >
                <p className="text-xs uppercase tracking-wider text-faint">
                  Your rights
                </p>
                <p className="text-sm text-fg mt-1">
                  Data access, erasure, human review, alternative assessment →
                </p>
              </Link>
            </section>

            <AppealForm sessionId={sessionId} />
          </>
        )}

        <footer className="pt-4 flex items-center justify-between text-xs text-faint">
          <p className="font-mono">session {sessionId}</p>
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
      <ComplianceFooter />
    </>
  );
}
