/**
 * One rubric axis on the scorecard (v3): score 0–10 + confidence interval +
 * qualitative band + evaluator agreement + summary + cited evidence.
 */
import { useState } from "react";

import type { ScorecardAxis } from "../types";
import AgreementPill from "./AgreementPill";
import BandChip from "./BandChip";
import ConfidenceBar from "./ConfidenceBar";
import EvidenceItem from "./EvidenceItem";

interface Props {
  axis: ScorecardAxis;
}

export default function ScoreAxis({ axis }: Props) {
  const [open, setOpen] = useState(true);
  return (
    <article className="rounded-lg border border-border bg-surface-2 p-5 space-y-3">
      <header className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <h3 className="text-lg font-medium text-fg">{axis.axis}</h3>
          {axis.flagged && (
            <p className="text-xs text-warning mt-1">
              ⚠ Flagged — evaluator's evidence did not match real session events.
            </p>
          )}
        </div>
        <div className="text-right shrink-0">
          <div className="flex items-baseline gap-2 justify-end">
            <span className="text-3xl font-semibold text-fg tabular-nums">
              {axis.score_0_10.toFixed(1)}
            </span>
            <span className="text-sm text-faint">/ 10</span>
          </div>
          <p className="text-[11px] text-muted font-mono tabular-nums mt-0.5">
            ± {axis.confidence_pm.toFixed(1)}
          </p>
        </div>
      </header>

      <ConfidenceBar
        score={axis.score_0_10}
        pm={axis.confidence_pm}
        band={axis.band as never}
      />

      <div className="flex items-center gap-2 pt-1">
        <BandChip band={axis.band as never} />
        <AgreementPill value={axis.agreement as never} />
      </div>

      <p className="text-sm text-muted leading-relaxed">{axis.summary}</p>

      {axis.evidence.length > 0 ? (
        <>
          <button
            type="button"
            onClick={() => setOpen((o) => !o)}
            className="text-xs uppercase tracking-wider text-faint hover:text-muted flex items-center gap-1.5"
            aria-expanded={open}
          >
            <span aria-hidden>{open ? "▾" : "▸"}</span>
            <span>
              Evidence
              <span className="text-faint normal-case font-normal ml-2">
                ({axis.evidence.length})
              </span>
            </span>
          </button>
          {open && (
            <ul className="space-y-2 pt-1">
              {axis.evidence.map((e, i) => (
                <EvidenceItem key={i} evidence={e} />
              ))}
            </ul>
          )}
        </>
      ) : (
        <p className="text-xs text-faint italic">No surviving evidence.</p>
      )}
    </article>
  );
}
