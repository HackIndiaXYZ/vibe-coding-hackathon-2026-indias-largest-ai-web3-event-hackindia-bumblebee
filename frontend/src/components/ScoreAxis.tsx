/**
 * One rubric axis on the scorecard: axis name, score (visual scale 1-5),
 * summary, and an expandable list of EvidenceItems.
 */
import { useState } from "react";

import type { ScorecardAxis } from "../types";
import EvidenceItem from "./EvidenceItem";

const SCORE_TONE: Record<number, string> = {
  1: "text-danger",
  2: "text-danger",
  3: "text-muted",
  4: "text-success",
  5: "text-success",
};

interface Props {
  axis: ScorecardAxis;
}

export default function ScoreAxis({ axis }: Props) {
  const [open, setOpen] = useState(true);
  return (
    <article className="rounded-lg border border-border bg-surface-2 p-5">
      <header className="flex items-start justify-between gap-4 mb-2">
        <div>
          <h3 className="text-lg font-medium text-fg">{axis.axis}</h3>
          {axis.flagged && (
            <p className="text-xs text-warning mt-1">
              ⚠ Flagged — evaluator's evidence did not match real session events.
            </p>
          )}
        </div>
        <div className="flex items-baseline gap-2">
          <span className={`text-3xl font-semibold ${SCORE_TONE[axis.score] ?? "text-fg"}`}>
            {axis.score}
          </span>
          <span className="text-sm text-faint">/ 5</span>
        </div>
      </header>
      <p className="text-sm text-muted leading-relaxed mb-3">{axis.summary}</p>

      {axis.evidence.length > 0 ? (
        <>
          <button
            type="button"
            onClick={() => setOpen((o) => !o)}
            className="text-xs uppercase tracking-wider text-faint hover:text-muted flex items-center gap-1.5 mb-3"
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
            <ul className="space-y-2">
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
