/**
 * One evidence card on the scorecard. Timestamp + quote (the hero) + reasoning.
 */
import type { ScorecardEvidence } from "../types";

function fmtTs(ms: number): string {
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  return `${m}:${(s % 60).toString().padStart(2, "0")}`;
}

interface Props {
  evidence: ScorecardEvidence;
}

export default function EvidenceItem({ evidence }: Props) {
  return (
    <li className="rounded-md border border-border bg-surface px-4 py-3">
      <div className="flex items-baseline justify-between gap-3 mb-2">
        <p className="text-xs text-faint font-mono tabular-nums">
          @ {fmtTs(evidence.ts_ms)}
        </p>
        <p className="text-[10px] text-faint">event #{evidence.event_id}</p>
      </div>
      <blockquote className="text-sm text-fg leading-relaxed border-l-2 border-accent/60 pl-3 mb-2 italic">
        "{evidence.quote}"
      </blockquote>
      <p className="text-xs text-muted leading-relaxed">{evidence.reasoning}</p>
    </li>
  );
}
