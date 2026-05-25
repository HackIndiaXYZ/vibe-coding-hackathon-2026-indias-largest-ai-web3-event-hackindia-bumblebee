/** Candidate rights page — the long version (§3.2 + §11). */
import ComplianceFooter from "../components/ComplianceFooter";

const RIGHTS = [
  {
    title: "Right to explanation",
    body:
      "Every candidate gets a per-axis plain-language explanation of how their session was scored, alongside the same cited evidence the recruiter sees. There is no two-screen model where the recruiter sees more than you do.",
  },
  {
    title: "Right to human review",
    body:
      "You can request that a human at the hiring company review your session within 14 days. The reviewer sees the full session telemetry, the original scorecard, and your reason for appeal. Day One does not adjudicate.",
  },
  {
    title: "Right to an alternative assessment process",
    body:
      "You can decline to take the Day One assessment and request an alternative — typically the hiring company's existing human-administered work-sample assessment. Day One surfaces the request; your employer's process is the alternative.",
  },
  {
    title: "Right to data access",
    body:
      "You can request a copy of all data we hold about your session (event log, scorecard, integrity context, appeal records).",
  },
  {
    title: "Right to data erasure",
    body:
      "You can request deletion. We honor erasure within 30 days from active systems and within the next backup cycle from backups.",
  },
  {
    title: "Right to NOT be auto-rejected",
    body:
      "Day One is sold to hiring companies only under a license that contractually forbids using our scorecard as a sole or automated decision basis. A human at the company decides.",
  },
];

export default function Rights() {
  return (
    <>
      <main id="main" className="max-w-3xl mx-auto px-4 py-10 space-y-8">
        <header className="space-y-3">
          <p className="text-xs uppercase tracking-wider text-faint">
            Your rights
          </p>
          <h1 className="text-3xl font-semibold tracking-tight text-fg">
            Six things Day One commits to, in plain English
          </h1>
          <p className="text-sm text-muted leading-relaxed">
            These are not legal boilerplate. They are product features. If we
            can't operate them, we don't ship.
          </p>
        </header>

        <section className="space-y-3">
          {RIGHTS.map((r) => (
            <article
              key={r.title}
              className="rounded-lg border border-border bg-surface p-5"
            >
              <h2 className="text-fg font-medium">{r.title}</h2>
              <p className="text-sm text-muted leading-relaxed mt-1.5">{r.body}</p>
            </article>
          ))}
        </section>

        <section className="rounded-lg border border-accent/40 bg-accent-soft/30 p-5 space-y-2">
          <p className="text-xs uppercase tracking-wider text-faint">
            How to exercise any of the above
          </p>
          <p className="text-sm text-fg leading-relaxed">
            Email{" "}
            <span className="font-mono text-accent">rights@dayone.example</span>{" "}
            from the address the assessment invite was sent to, naming the
            right you wish to exercise. Acknowledgement within 3 business
            days; resolution within the regulatory window.
          </p>
        </section>
      </main>
      <ComplianceFooter />
    </>
  );
}
