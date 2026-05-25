/**
 * Recruiter view of a single session. Same evidence-cited scorecard the
 * candidate sees + a reviewer "adjust" affordance (mock for v3 demo —
 * actual override goes through the human-review pathway).
 */
import { useEffect } from "react";
import { Link, useParams } from "react-router-dom";

import ComplianceFooter from "../components/ComplianceFooter";
import FormatBadge from "../components/FormatBadge";
import IntegrityContextEl from "../components/IntegrityContext";
import ScoreAxis from "../components/ScoreAxis";
import { useStore } from "../state/store";

export default function RecruiterSession() {
  const { sessionId = "" } = useParams();
  const scorecard = useStore((s) => s.scorecard);
  const loading = useStore((s) => s.scorecardLoading);
  const error = useStore((s) => s.lastError);
  const loadSession = useStore((s) => s.loadSession);
  const loadScorecard = useStore((s) => s.loadScorecard);

  useEffect(() => {
    if (!sessionId) return;
    void loadSession(sessionId).then(() => loadScorecard());
  }, [sessionId, loadSession, loadScorecard]);

  return (
    <>
      <main id="main" className="max-w-4xl mx-auto px-4 py-8 space-y-8">
        <nav className="text-xs text-muted">
          <Link to="/recruiter" className="hover:text-fg">
            ← Sessions
          </Link>
        </nav>
        <header className="space-y-3">
          <p className="text-xs uppercase tracking-wider text-faint">
            Reviewer view · same evidence the candidate sees
          </p>
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="text-3xl font-semibold tracking-tight text-fg">
              Session review
            </h1>
            {scorecard && (
              <FormatBadge
                format={scorecard.format}
                size="md"
                practice={scorecard.is_practice}
              />
            )}
          </div>
          <p className="text-sm text-muted leading-relaxed">
            You decide. Day One does not. Adjust an axis only after reading
            the cited evidence — every change is audit-logged.
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
            <section className="space-y-4">
              {scorecard.axes.map((a) => (
                <div key={a.axis} className="space-y-2">
                  <ScoreAxis axis={a} />
                  <div className="flex items-center justify-end gap-2 text-xs">
                    <button
                      type="button"
                      onClick={() =>
                        alert(
                          `Mock: adjust "${a.axis}" — a real recruiter would post a new score with rationale; the change would land on the audit log.`,
                        )
                      }
                      className="px-2 py-1 rounded-md border border-border text-muted hover:text-fg hover:border-border-strong"
                    >
                      Adjust score
                    </button>
                    <button
                      type="button"
                      onClick={() =>
                        alert("Mock: flag this axis for ensemble re-run.")
                      }
                      className="px-2 py-1 rounded-md border border-border text-muted hover:text-fg hover:border-border-strong"
                    >
                      Re-run axis
                    </button>
                  </div>
                </div>
              ))}
            </section>

            <IntegrityContextEl context={scorecard.integrity} format={scorecard.format} />

            <section className="rounded-lg border border-border bg-surface p-5">
              <p className="text-xs uppercase tracking-wider text-faint mb-2">
                Next step
              </p>
              <p className="text-sm text-muted leading-relaxed">
                Make the hire / no-hire / advance decision in your ATS — Day
                One never automates that for you. The scorecard, the evidence,
                and the integrity context above are the inputs. Your judgment
                is the decision.
              </p>
            </section>
          </>
        )}
      </main>
      <ComplianceFooter />
    </>
  );
}
