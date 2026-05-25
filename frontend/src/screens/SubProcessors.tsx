/** Sub-processor disclosure (§3.2 / §11.4). */
import ComplianceFooter from "../components/ComplianceFooter";

const PROCESSORS = [
  {
    name: "Google Gemini API",
    function: "LLM inference for the cast (Format A), the AI assistant (Format A), and evaluators (both Formats).",
    region: "US / multi-region",
    dataCategories: "Prompts (scenario / events / evaluator instructions). No PII fields persist beyond Google's stated retention.",
  },
  {
    name: "SQLite (local)",
    function: "Session, event log, scorecard, appeal persistence.",
    region: "Customer-owned infrastructure",
    dataCategories: "Session data per the customer's retention contract (default: 24 months active).",
  },
];

export default function SubProcessors() {
  return (
    <>
      <main id="main" className="max-w-3xl mx-auto px-4 py-10 space-y-8">
        <header className="space-y-3">
          <p className="text-xs uppercase tracking-wider text-faint">
            Sub-processors
          </p>
          <h1 className="text-3xl font-semibold tracking-tight text-fg">
            Who else touches your session data
          </h1>
          <p className="text-sm text-muted leading-relaxed">
            Maintained publicly per §3.2 of the v3 product spec. Updated as
            soon as a new sub-processor is onboarded.
          </p>
        </header>

        <section className="rounded-lg border border-border bg-surface overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-surface-2/60 text-faint text-xs uppercase tracking-wider">
              <tr>
                <th className="text-left px-4 py-2 font-normal">Processor</th>
                <th className="text-left px-4 py-2 font-normal">Function</th>
                <th className="text-left px-4 py-2 font-normal">Region</th>
                <th className="text-left px-4 py-2 font-normal">Data categories</th>
              </tr>
            </thead>
            <tbody>
              {PROCESSORS.map((p) => (
                <tr key={p.name} className="border-t border-border">
                  <td className="px-4 py-3 text-fg">{p.name}</td>
                  <td className="px-4 py-3 text-muted">{p.function}</td>
                  <td className="px-4 py-3 text-muted">{p.region}</td>
                  <td className="px-4 py-3 text-muted">{p.dataCategories}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </main>
      <ComplianceFooter />
    </>
  );
}
