/**
 * Integrity context (§6.4) — descriptive, never adjudicatory.
 *
 * Surfaced as its own dedicated section on the scorecard, clearly separated
 * from rubric axes. We do NOT produce an "integrity score".
 */
import type { IntegrityContext as Ctx } from "../types";

interface Props {
  context: Ctx;
  format: "A" | "B";
}

export default function IntegrityContext({ context, format }: Props) {
  return (
    <section className="rounded-lg border border-border bg-surface p-5 space-y-3">
      <header>
        <p className="text-xs uppercase tracking-wider text-faint">
          Integrity Context
        </p>
        <p className="text-xs text-muted leading-relaxed mt-1">
          Descriptive. Never scored. We do not deploy biometrics, webcam, or
          keystroke surveillance. The recruiter sees this section. So do you.
        </p>
      </header>

      <dl className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
        <Stat
          label="Tab switches"
          value={context.tab_focus_lost_count.toString()}
        />
        <Stat
          label="Time away"
          value={`${Math.round(context.tab_focus_total_away_ms / 1000)}s`}
        />
        <Stat label="Paste events" value={context.paste_event_count.toString()} />
        <Stat
          label="External bytes"
          value={context.paste_external_bytes.toString()}
        />
        {format === "A" && (
          <>
            <Stat
              label="AI assistant turns"
              value={context.ai_assistant_turn_count.toString()}
            />
            <Stat
              label="Cast messages"
              value={context.cast_message_count.toString()}
            />
          </>
        )}
      </dl>

      <ul className="text-xs text-muted space-y-1 list-disc pl-5">
        {context.notes.map((n, i) => (
          <li key={i}>{n}</li>
        ))}
      </ul>
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md bg-surface-2 border border-border p-2">
      <p className="text-[10px] uppercase tracking-wider text-faint">{label}</p>
      <p className="text-fg font-mono text-sm mt-0.5 tabular-nums">{value}</p>
    </div>
  );
}
