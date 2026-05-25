/**
 * Appeal CTA — collapsible form. POSTs a human-review request (§11.5).
 */
import { useState } from "react";

import { api } from "../api/client";

interface Props {
  sessionId: string;
}

export default function AppealForm({ sessionId }: Props) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submittedId, setSubmittedId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const submit = async () => {
    setSubmitting(true);
    setError(null);
    try {
      const r = await api.postAppeal(sessionId, reason.trim());
      setSubmittedId(r.id);
      setReason("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSubmitting(false);
    }
  };

  if (submittedId) {
    return (
      <section className="rounded-lg border border-success/40 bg-success/10 p-4 text-sm text-fg">
        Appeal #{submittedId} routed to the hiring company. A human reviewer
        will respond within 14 days. You'll be notified by email.
      </section>
    );
  }

  return (
    <section className="rounded-lg border border-border bg-surface p-4">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="w-full flex items-center justify-between text-left"
      >
        <span>
          <span className="text-xs uppercase tracking-wider text-faint block">
            Don't think this represents your work?
          </span>
          <span className="text-sm text-fg">Request human review of this scorecard →</span>
        </span>
        <span className="text-faint" aria-hidden>
          {open ? "▾" : "▸"}
        </span>
      </button>
      {open && (
        <div className="mt-3 space-y-2">
          <p className="text-xs text-muted leading-relaxed">
            Routed to your hiring company's authorized reviewer with the full
            session telemetry. Day One does not adjudicate the appeal.
          </p>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={4}
            placeholder="Briefly: what about the scorecard does not match your experience of the session?"
            className="w-full bg-bg border border-border rounded-md px-3 py-2 text-sm placeholder:text-faint focus:outline-none focus:border-accent"
          />
          {error && <p className="text-xs text-danger">{error}</p>}
          <div className="flex justify-end">
            <button
              type="button"
              onClick={submit}
              disabled={submitting || reason.trim().length < 8}
              className="rounded-md bg-accent text-black text-sm font-medium px-3 py-1.5 disabled:opacity-40"
            >
              {submitting ? "Submitting…" : "Submit appeal"}
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
