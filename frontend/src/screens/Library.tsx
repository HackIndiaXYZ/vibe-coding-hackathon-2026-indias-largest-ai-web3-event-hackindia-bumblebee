/**
 * Library (§9) — surfaces the Format A scenario template and Format B task
 * template inventory. v1-GA-honest mock: lists library size, anti-leakage
 * architecture, customer-authoring lead times.
 */
import ComplianceFooter from "../components/ComplianceFooter";
import FormatBadge from "../components/FormatBadge";

const SCENARIO_TEMPLATES_A = [
  {
    role: "Junior Full-Stack Developer",
    domain: "B2B SaaS · invoicing",
    twists: 12,
    personas: 14,
  },
  {
    role: "Junior Full-Stack Developer",
    domain: "B2B SaaS · observability",
    twists: 10,
    personas: 12,
  },
  {
    role: "Mid-level Backend Engineer",
    domain: "B2B SaaS · billing",
    twists: 11,
    personas: 12,
  },
  {
    role: "Mid-level Backend Engineer",
    domain: "B2B SaaS · support tooling",
    twists: 10,
    personas: 13,
  },
  {
    role: "Platform Engineer",
    domain: "B2B SaaS · observability",
    twists: 9,
    personas: 11,
  },
];

const TASK_TEMPLATES_B = [
  { role: "Junior Full-Stack Developer", tasks: 28, kinds: "Algorithms · API" },
  { role: "Mid-level Backend Engineer", tasks: 34, kinds: "Algorithms · API · refactor" },
  { role: "Platform Engineer", tasks: 22, kinds: "Reliability · debugging" },
];

export default function Library() {
  return (
    <>
      <main id="main" className="max-w-5xl mx-auto px-4 py-10 space-y-10">
        <header className="space-y-3">
          <p className="text-xs uppercase tracking-wider text-faint">
            Day One · Library
          </p>
          <h1 className="text-3xl font-semibold tracking-tight text-fg">
            Scenarios &amp; tasks
          </h1>
          <p className="text-sm text-muted max-w-2xl leading-relaxed">
            The library is the central intellectual property of Day One. What
            makes scoring psychometrically defensible (sessions are comparable)
            and leakage-resistant (sessions are not identical). Every template
            below is human-authored, psychometrically reviewed, and combinatorially
            randomized at session-instantiation time.
          </p>
        </header>

        <section className="grid sm:grid-cols-3 gap-4">
          <Stat
            label="Format A scenarios"
            value={`${SCENARIO_TEMPLATES_A.length} templates`}
            sub="× 10+ twists × 10+ personas × 3 cast roles"
          />
          <Stat
            label="Format B tasks"
            value={`${TASK_TEMPLATES_B.reduce((a, t) => a + t.tasks, 0)} tasks`}
            sub="across role specializations"
          />
          <Stat
            label="Total instantiations"
            value="450,000+"
            sub="combinatorial space at GA"
          />
        </section>

        <section className="rounded-lg border border-border bg-surface p-5 space-y-3">
          <p className="text-xs uppercase tracking-wider text-faint">
            Anti-leakage architecture
          </p>
          <ul className="text-sm text-muted leading-relaxed list-disc pl-5 space-y-1">
            <li>
              Format A: every session draws a unique combination of (twist, cast
              personas, surface details) from the chosen template.
            </li>
            <li>
              Format B: large task library + customer-selectable task sets +
              periodic task rotation + public-domain task quarantine.
            </li>
            <li>
              Continuous monitoring for systematic leakage signals (clustered
              performance spikes, social-media monitoring).
            </li>
            <li>
              Customer-authored content lives in a per-customer private library
              — never pollutes the platform-wide pool.
            </li>
          </ul>
        </section>

        <section className="space-y-4">
          <h2 className="text-xs uppercase tracking-wider text-faint">
            Format A · scenario templates
          </h2>
          <div className="rounded-lg border border-border bg-surface overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-surface-2/60 text-faint text-xs uppercase tracking-wider">
                <tr>
                  <th className="text-left px-4 py-2 font-normal">Format</th>
                  <th className="text-left px-4 py-2 font-normal">Role</th>
                  <th className="text-left px-4 py-2 font-normal">Domain</th>
                  <th className="text-right px-4 py-2 font-normal">Twist variants</th>
                  <th className="text-right px-4 py-2 font-normal">Persona pool</th>
                </tr>
              </thead>
              <tbody>
                {SCENARIO_TEMPLATES_A.map((t, i) => (
                  <tr key={i} className="border-t border-border">
                    <td className="px-4 py-2.5">
                      <FormatBadge format="A" />
                    </td>
                    <td className="px-4 py-2.5 text-fg">{t.role}</td>
                    <td className="px-4 py-2.5 text-muted">{t.domain}</td>
                    <td className="px-4 py-2.5 text-right text-muted font-mono tabular-nums">
                      {t.twists}
                    </td>
                    <td className="px-4 py-2.5 text-right text-muted font-mono tabular-nums">
                      {t.personas}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="space-y-4">
          <h2 className="text-xs uppercase tracking-wider text-faint">
            Format B · task templates
          </h2>
          <div className="rounded-lg border border-border bg-surface overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-surface-2/60 text-faint text-xs uppercase tracking-wider">
                <tr>
                  <th className="text-left px-4 py-2 font-normal">Format</th>
                  <th className="text-left px-4 py-2 font-normal">Role</th>
                  <th className="text-left px-4 py-2 font-normal">Kinds</th>
                  <th className="text-right px-4 py-2 font-normal">Task count</th>
                </tr>
              </thead>
              <tbody>
                {TASK_TEMPLATES_B.map((t, i) => (
                  <tr key={i} className="border-t border-border">
                    <td className="px-4 py-2.5">
                      <FormatBadge format="B" />
                    </td>
                    <td className="px-4 py-2.5 text-fg">{t.role}</td>
                    <td className="px-4 py-2.5 text-muted">{t.kinds}</td>
                    <td className="px-4 py-2.5 text-right text-muted font-mono tabular-nums">
                      {t.tasks}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="rounded-lg border border-border bg-surface p-5 space-y-3">
          <p className="text-xs uppercase tracking-wider text-faint">
            Customer authoring (§12.4)
          </p>
          <p className="text-sm text-muted leading-relaxed">
            Customers can author scenarios (Format A) and tasks (Format B)
            specific to their company — subject to our compliance review for
            construct validity, adverse-impact screening, and format
            consistency. Approved content lives in the customer's private
            library and never pollutes the platform-wide pool. Lead times:
            scenarios 8 weeks standard, tasks 4 weeks standard.
          </p>
        </section>
      </main>
      <ComplianceFooter />
    </>
  );
}

function Stat({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-surface p-4">
      <p className="text-[10px] uppercase tracking-wider text-faint">{label}</p>
      <p className="text-2xl text-fg font-semibold tabular-nums mt-1">{value}</p>
      <p className="text-xs text-muted mt-0.5">{sub}</p>
    </div>
  );
}
