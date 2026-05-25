/**
 * Recruiter Dashboard (§12.1).
 *
 * Reads /recruiter/sessions — real sessions persisted by the backend. Each
 * row is a candidate session with format, status, and axis summary.
 */
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import BandChip from "../components/BandChip";
import ComplianceFooter from "../components/ComplianceFooter";
import FormatBadge from "../components/FormatBadge";
import { api } from "../api/client";
import type { RecruiterSessionRow } from "../types";

export default function RecruiterDashboard() {
  const [rows, setRows] = useState<RecruiterSessionRow[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [formatFilter, setFormatFilter] = useState<"all" | "A" | "B">("all");

  useEffect(() => {
    api
      .listRecruiterSessions()
      .then(setRows)
      .catch((e) => setError((e as Error).message));
  }, []);

  const filtered = (rows ?? []).filter((r) =>
    formatFilter === "all" ? true : r.format === formatFilter,
  );

  return (
    <>
      <main id="main" className="max-w-6xl mx-auto px-4 py-10 space-y-8">
        <header className="space-y-3">
          <p className="text-xs uppercase tracking-wider text-faint">
            Day One · Recruiter
          </p>
          <h1 className="text-3xl font-semibold tracking-tight text-fg">
            Sessions
          </h1>
          <p className="text-sm text-muted max-w-2xl leading-relaxed">
            Practice runs are hidden. Each row links to the same evidence-cited
            scorecard the candidate sees. Day One does not adjudicate hire
            decisions — that is your job, supported by the evidence here.
          </p>
        </header>

        <section className="flex items-center gap-2">
          {(["all", "A", "B"] as const).map((f) => (
            <button
              key={f}
              type="button"
              onClick={() => setFormatFilter(f)}
              className={`text-xs px-3 py-1.5 rounded-md border ${
                formatFilter === f
                  ? "border-accent text-accent bg-accent-soft/40"
                  : "border-border text-muted hover:text-fg"
              }`}
            >
              {f === "all" ? "All formats" : `Format ${f}`}
            </button>
          ))}
        </section>

        {error && (
          <p className="text-danger text-sm" role="alert">
            {error}
          </p>
        )}

        {rows && rows.length === 0 && (
          <div className="rounded-lg border border-border bg-surface p-8 text-center text-muted text-sm">
            No completed sessions yet.{" "}
            <Link to="/" className="text-accent hover:underline">
              Run one →
            </Link>
          </div>
        )}

        {rows && rows.length > 0 && (
          <section className="rounded-lg border border-border bg-surface overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-surface-2/60 text-faint text-xs uppercase tracking-wider">
                <tr>
                  <th className="text-left px-4 py-2 font-normal">Candidate</th>
                  <th className="text-left px-4 py-2 font-normal">Role</th>
                  <th className="text-left px-4 py-2 font-normal">Format</th>
                  <th className="text-left px-4 py-2 font-normal">Status</th>
                  <th className="text-left px-4 py-2 font-normal">Axis bands</th>
                  <th className="text-right px-4 py-2 font-normal">When</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((r) => (
                  <tr
                    key={r.id}
                    className="border-t border-border hover:bg-surface-2/40 transition-colors"
                  >
                    <td className="px-4 py-3">
                      <Link
                        to={`/recruiter/${r.id}`}
                        className="text-fg hover:text-accent"
                      >
                        {r.candidate_label || (
                          <span className="font-mono text-muted text-xs">
                            {r.id.slice(0, 10)}…
                          </span>
                        )}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-muted">{r.role}</td>
                    <td className="px-4 py-3">
                      <FormatBadge format={r.format} />
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs text-muted uppercase tracking-wider">
                        {r.status}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {r.axes_summary.length === 0 && (
                          <span className="text-xs text-faint italic">
                            no scorecard
                          </span>
                        )}
                        {r.axes_summary.map((a) => (
                          <span
                            key={a.axis}
                            title={`${a.axis} · ${a.score_0_10.toFixed(1)}/10`}
                          >
                            <BandChip band={a.band as never} />
                          </span>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right text-xs text-faint font-mono">
                      {r.ended_at ? new Date(r.ended_at).toLocaleString() : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        )}
      </main>
      <ComplianceFooter />
    </>
  );
}
