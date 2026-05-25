/** Collapsible task brief in the top bar — works for both Formats. */
import { useState } from "react";

import type { AnyScenario } from "../types";

interface Props {
  scenario: AnyScenario | null;
}

export default function TaskBrief({ scenario }: Props) {
  const [open, setOpen] = useState(false);
  if (!scenario) {
    return <span className="text-sm text-faint">(no scenario)</span>;
  }
  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="text-sm text-muted hover:text-fg flex items-center gap-1.5 transition-colors"
        aria-expanded={open}
      >
        <span aria-hidden>{open ? "▾" : "▸"}</span>
        <span className="font-medium text-fg">{scenario.company_name}</span>
        <span className="text-faint">·</span>
        <span>{scenario.tasks.length} tasks</span>
      </button>
      {open && (
        <div className="absolute left-0 top-full mt-2 z-10 w-[36rem] max-w-[80vw] rounded-lg border border-border bg-surface p-4 shadow-xl">
          <p className="text-xs uppercase tracking-wider text-faint mb-1">Company</p>
          <p className="text-sm text-muted mb-3">{scenario.company_context}</p>
          <p className="text-xs uppercase tracking-wider text-faint mb-2">Tasks</p>
          <ol className="space-y-3">
            {scenario.tasks.map((t, i) => (
              <li key={t.id} className="text-sm">
                <p className="font-medium text-fg">
                  <span className="text-faint mr-2">{i + 1}.</span>
                  {t.title}
                </p>
                <p className="text-muted text-xs mt-1 leading-relaxed">{t.description}</p>
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}
