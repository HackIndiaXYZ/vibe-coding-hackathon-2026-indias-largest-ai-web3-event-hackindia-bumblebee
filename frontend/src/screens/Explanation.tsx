/**
 * Right-to-explanation screen (§11.4).
 *
 * Plain-language description of every axis, with explicit "what we measure"
 * and "what we don't measure" pairs. Rights list. Sub-processor list.
 */
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import ComplianceFooter from "../components/ComplianceFooter";
import FormatBadge from "../components/FormatBadge";
import { api } from "../api/client";
import type { Explanation as ExplanationT } from "../types";

export default function Explanation() {
  const { sessionId = "" } = useParams();
  const [data, setData] = useState<ExplanationT | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!sessionId) return;
    api
      .getExplanation(sessionId)
      .then(setData)
      .catch((e) => setError((e as Error).message));
  }, [sessionId]);

  if (error) {
    return (
      <main id="main" className="min-h-screen flex items-center justify-center p-8">
        <p className="text-danger text-sm">{error}</p>
      </main>
    );
  }
  if (!data) {
    return (
      <main id="main" className="min-h-screen flex items-center justify-center p-8">
        <p className="text-muted text-sm">Loading…</p>
      </main>
    );
  }

  return (
    <>
      <main id="main" className="max-w-3xl mx-auto px-4 py-10 space-y-8">
        <header className="space-y-3">
          <p className="text-xs uppercase tracking-wider text-faint">
            Right to explanation
          </p>
          <div className="flex items-center gap-2 flex-wrap">
            <h1 className="text-3xl font-semibold tracking-tight text-fg">
              How this scorecard was produced
            </h1>
            <FormatBadge format={data.format} size="md" />
          </div>
          <p className="text-muted leading-relaxed">{data.intro}</p>
        </header>

        <section className="space-y-3">
          <p className="text-xs uppercase tracking-wider text-faint">
            What each axis means
          </p>
          {data.per_axis.map((a) => (
            <article
              key={a.axis}
              className="rounded-lg border border-border bg-surface p-5 space-y-3"
            >
              <h2 className="text-lg font-medium text-fg">{a.axis}</h2>
              <p className="text-sm text-muted leading-relaxed">{a.plain_language}</p>
              <div className="grid sm:grid-cols-2 gap-3 text-sm">
                <div className="rounded-md bg-success/5 border border-success/30 p-3">
                  <p className="text-xs uppercase tracking-wider text-success mb-1">
                    What we measure
                  </p>
                  <p className="text-muted leading-relaxed">{a.what_we_measure}</p>
                </div>
                <div className="rounded-md bg-danger/5 border border-danger/30 p-3">
                  <p className="text-xs uppercase tracking-wider text-danger mb-1">
                    What we don't
                  </p>
                  <p className="text-muted leading-relaxed">{a.what_we_dont_measure}</p>
                </div>
              </div>
            </article>
          ))}
        </section>

        <section className="rounded-lg border border-border bg-surface p-5 space-y-3">
          <p className="text-xs uppercase tracking-wider text-faint">Your rights</p>
          <ul className="text-sm text-muted leading-relaxed space-y-1 list-disc pl-5">
            {data.rights.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </section>

        <section className="rounded-lg border border-border bg-surface p-5 space-y-3">
          <p className="text-xs uppercase tracking-wider text-faint">
            Sub-processors
          </p>
          <ul className="text-sm text-muted leading-relaxed space-y-2">
            {data.sub_processors.map((p, i) => (
              <li key={i}>· {p}</li>
            ))}
          </ul>
        </section>

        <footer className="pt-4">
          <Link
            to={`/scorecard/${sessionId}`}
            className="text-sm text-muted hover:text-fg transition-colors"
          >
            ← Back to scorecard
          </Link>
        </footer>
      </main>
      <ComplianceFooter />
    </>
  );
}
