/**
 * Compliance footer — visible across most non-workspace screens.
 *
 * Surfaces the AEDT acknowledgement, sub-processor pointer, and rights
 * pointer at all times — per §3.2. Quiet visually; loud semantically.
 */
import { Link } from "react-router-dom";

export default function ComplianceFooter() {
  return (
    <footer className="mt-16 border-t border-border bg-surface/40">
      <div className="max-w-7xl mx-auto px-4 py-6 grid sm:grid-cols-3 gap-6 text-xs text-muted">
        <div>
          <p className="uppercase tracking-wider text-faint mb-1.5">
            Automated Employment Decision Tool
          </p>
          <p className="leading-relaxed">
            Day One is an AEDT under NYC Local Law 144 and a high-risk AI
            system under the EU AI Act, Annex III §4. We say so up front.
          </p>
        </div>
        <div>
          <p className="uppercase tracking-wider text-faint mb-1.5">
            Decision support, not verdict
          </p>
          <p className="leading-relaxed">
            A human at the hiring company makes the hire decision. Our license
            forbids customers from automating that decision off our scorecard.
          </p>
        </div>
        <div>
          <p className="uppercase tracking-wider text-faint mb-1.5">
            Your rights
          </p>
          <ul className="space-y-0.5 leading-relaxed">
            <li>
              <Link to="/rights" className="hover:text-fg transition-colors">
                Data, explanation, appeal, alternative assessment →
              </Link>
            </li>
            <li>
              <Link
                to="/sub-processors"
                className="hover:text-fg transition-colors"
              >
                Sub-processor list →
              </Link>
            </li>
            <li>
              <Link to="/fairness" className="hover:text-fg transition-colors">
                Bias audit results →
              </Link>
            </li>
          </ul>
        </div>
      </div>
      <div className="border-t border-border/60">
        <p className="max-w-7xl mx-auto px-4 py-3 text-[10px] text-faint">
          v3.0 · English only · Desktop only · No biometric anti-cheat by
          default · WCAG 2.2 AA
        </p>
      </div>
    </footer>
  );
}
