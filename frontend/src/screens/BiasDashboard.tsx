/**
 * Fairness / bias dashboard mock (§10).
 *
 * Per-format bias audit summary, 4/5ths-rule selection rates, score
 * distribution by demographic group (where lawfully collected, opt-in).
 * Numbers are illustrative for the v3 demo; the architecture is real.
 */
import ComplianceFooter from "../components/ComplianceFooter";
import FormatBadge from "../components/FormatBadge";

const MOCK = {
  A: {
    auditDate: "2026-Q2",
    sampled: 4128,
    fourFifths: 0.91,
    diffValidity: 0.04,
    distribution: [
      { group: "Self-reported · Women", mean: 6.8, sd: 1.4 },
      { group: "Self-reported · Men", mean: 6.9, sd: 1.5 },
      { group: "Asian", mean: 7.1, sd: 1.4 },
      { group: "Black", mean: 6.7, sd: 1.5 },
      { group: "Hispanic", mean: 6.7, sd: 1.5 },
      { group: "White", mean: 6.9, sd: 1.4 },
    ],
  },
  B: {
    auditDate: "2026-Q2",
    sampled: 5824,
    fourFifths: 0.93,
    diffValidity: 0.03,
    distribution: [
      { group: "Self-reported · Women", mean: 6.5, sd: 1.7 },
      { group: "Self-reported · Men", mean: 6.6, sd: 1.7 },
      { group: "Asian", mean: 6.8, sd: 1.6 },
      { group: "Black", mean: 6.4, sd: 1.8 },
      { group: "Hispanic", mean: 6.4, sd: 1.7 },
      { group: "White", mean: 6.6, sd: 1.7 },
    ],
  },
};

export default function BiasDashboard() {
  return (
    <>
      <main id="main" className="max-w-5xl mx-auto px-4 py-10 space-y-10">
        <header className="space-y-3">
          <p className="text-xs uppercase tracking-wider text-faint">
            Day One · Fairness
          </p>
          <h1 className="text-3xl font-semibold tracking-tight text-fg">
            Bias monitoring — per Format
          </h1>
          <p className="text-sm text-muted max-w-2xl leading-relaxed">
            Day One commissions independent third-party bias audits per Format
            on a rolling quarterly basis. The most recent audit summary is
            shown below. Numbers are illustrative for this preview; the
            architecture is real (§10).
          </p>
        </header>

        {(["A", "B"] as const).map((fmt) => {
          const m = MOCK[fmt];
          return (
            <section
              key={fmt}
              className="rounded-xl border border-border bg-surface p-6 space-y-5"
            >
              <header className="flex items-center justify-between flex-wrap gap-2">
                <div className="flex items-center gap-2">
                  <FormatBadge format={fmt} size="md" />
                  <h2 className="text-xl text-fg font-medium">
                    {fmt === "A"
                      ? "Multi-Agent Work Simulation"
                      : "Solo Technical Assessment"}
                  </h2>
                </div>
                <span className="text-xs text-faint">Audit · {m.auditDate}</span>
              </header>

              <div className="grid sm:grid-cols-3 gap-3">
                <Stat label="Sessions sampled" value={m.sampled.toLocaleString()} />
                <Stat
                  label="4/5ths rule selection ratio"
                  value={m.fourFifths.toFixed(2)}
                  good={m.fourFifths >= 0.8}
                />
                <Stat
                  label="Differential validity |Δr|"
                  value={m.diffValidity.toFixed(2)}
                  good={m.diffValidity <= 0.1}
                />
              </div>

              <div>
                <p className="text-xs uppercase tracking-wider text-faint mb-2">
                  Score distribution (mean ± 1 SD on 0–10)
                </p>
                <ul className="space-y-2">
                  {m.distribution.map((row) => (
                    <li key={row.group} className="flex items-center gap-3">
                      <span className="w-48 text-sm text-muted">
                        {row.group}
                      </span>
                      <span className="flex-1 relative h-2 rounded-full bg-surface-3">
                        <span
                          className="absolute top-0 h-full bg-accent/40 rounded-full"
                          style={{
                            left: `${(row.mean - row.sd) * 10}%`,
                            width: `${row.sd * 20}%`,
                          }}
                        />
                        <span
                          className="absolute top-0 h-full w-[2px] bg-accent"
                          style={{ left: `calc(${row.mean * 10}% - 1px)` }}
                        />
                      </span>
                      <span className="w-16 text-right text-xs text-fg font-mono tabular-nums">
                        {row.mean.toFixed(1)}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>

              <p className="text-xs text-muted leading-relaxed">
                Adverse-impact threshold met across all monitored groups for
                this audit window. Demographic data was self-reported, opt-in,
                and never available to evaluators during scoring.
              </p>
            </section>
          );
        })}

        <section className="rounded-lg border border-border bg-surface p-5 space-y-3">
          <p className="text-xs uppercase tracking-wider text-faint">
            When we detect bias
          </p>
          <ol className="text-sm text-muted leading-relaxed list-decimal pl-5 space-y-1">
            <li>Investigation by our I-O psychology consultant and engineering.</li>
            <li>Affected customers notified within 30 days.</li>
            <li>
              Remediation: rubric revision, evaluator re-tune, scenario/task
              retirement, customer-authored-content revision as appropriate.
            </li>
            <li>Post-remediation monitoring against the prior baseline for 90 days.</li>
            <li>Material findings published in the next quarterly audit.</li>
          </ol>
        </section>
      </main>
      <ComplianceFooter />
    </>
  );
}

function Stat({
  label,
  value,
  good,
}: {
  label: string;
  value: string;
  good?: boolean;
}) {
  return (
    <div className="rounded-md border border-border bg-surface-2 p-3">
      <p className="text-[10px] uppercase tracking-wider text-faint">{label}</p>
      <p
        className={`text-xl font-semibold mt-1 tabular-nums ${
          good === undefined ? "text-fg" : good ? "text-success" : "text-warning"
        }`}
      >
        {value}
      </p>
    </div>
  );
}
