/** Evaluator-agreement pill (high / medium / low / divergent). */
import type { EvaluatorAgreement } from "../types";

const TONE: Record<EvaluatorAgreement, string> = {
  high: "bg-success/15 text-success border-success/30",
  medium: "bg-accent/15 text-accent border-accent/30",
  low: "bg-warning/15 text-warning border-warning/30",
  divergent: "bg-danger/15 text-danger border-danger/40",
};

const LABEL: Record<EvaluatorAgreement, string> = {
  high: "Evaluators agreed",
  medium: "Some variance",
  low: "Thin evidence",
  divergent: "Divergent — review",
};

export default function AgreementPill({ value }: { value: EvaluatorAgreement }) {
  return (
    <span
      className={`inline-block rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-wider ${TONE[value] ?? ""}`}
      title="How consistent evaluator samples were on this axis"
    >
      {LABEL[value]}
    </span>
  );
}
