/**
 * Practice Hub — free, unlimited, no-stakes per-format runs (§11.2).
 *
 * Functionally identical to creating a real session, except `is_practice=true`
 * so the session is excluded from recruiter listings.
 */
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import ComplianceFooter from "../components/ComplianceFooter";
import FormatBadge from "../components/FormatBadge";
import { useStore } from "../state/store";
import type { SessionFormat } from "../types";

export default function PracticeHub() {
  const navigate = useNavigate();
  const createSession = useStore((s) => s.createSession);
  const reset = useStore((s) => s.reset);
  const accessibility = useStore((s) => s.accessibility);
  const [busy, setBusy] = useState<SessionFormat | null>(null);
  const [error, setError] = useState<string | null>(null);

  const start = async (format: SessionFormat) => {
    reset();
    setBusy(format);
    setError(null);
    try {
      const sid = await createSession({
        role: "Junior Full-Stack Developer",
        format,
        session_minutes: 30,
        accessibility,
        is_practice: true,
        candidate_label: "Practice run",
      });
      navigate(`/disclosure/${sid}`);
    } catch (e) {
      setError((e as Error).message);
      setBusy(null);
    }
  };

  return (
    <>
      <main id="main" className="max-w-4xl mx-auto px-4 py-10 space-y-10">
        <header className="space-y-3">
          <p className="text-xs uppercase tracking-wider text-faint">
            Practice Mode · free · scored nowhere
          </p>
          <h1 className="text-3xl font-semibold tracking-tight text-fg">
            Try a session. No stakes.
          </h1>
          <p className="text-muted max-w-2xl leading-relaxed">
            Most candidates have never taken an assessment in this format.
            Practice Mode gives you a 30-minute run in either format — same
            engine, no recruiter visibility, no scoring on file. Signals respect
            for your time and your learning curve. Per v3 §11.2.
          </p>
        </header>

        <section className="grid sm:grid-cols-2 gap-4">
          <PracticeCard
            format="A"
            busy={busy === "A"}
            onStart={() => start("A")}
          />
          <PracticeCard
            format="B"
            busy={busy === "B"}
            onStart={() => start("B")}
          />
        </section>

        {error && (
          <p className="text-sm text-danger" role="alert">
            {error}
          </p>
        )}
      </main>
      <ComplianceFooter />
    </>
  );
}

function PracticeCard({
  format,
  busy,
  onStart,
}: {
  format: SessionFormat;
  busy: boolean;
  onStart: () => void;
}) {
  const isA = format === "A";
  return (
    <article className="rounded-xl border border-border bg-surface p-5 space-y-3">
      <div className="flex items-center justify-between gap-2">
        <FormatBadge format={format} size="md" practice />
        <span className="text-[10px] text-faint">~30 min</span>
      </div>
      <h2 className="text-xl text-fg font-medium">
        {isA ? "Practice: simulation" : "Practice: solo coding"}
      </h2>
      <p className="text-sm text-muted leading-relaxed">
        {isA
          ? "Cast agents react. The twist fires. The AI assistant is available. Identical to the real Format A session structure."
          : "Code-only task set. No cast. No AI in-surface. Identical to the real Format B session structure."}
      </p>
      <button
        type="button"
        onClick={onStart}
        disabled={busy}
        className="w-full rounded-md bg-accent text-black text-sm font-medium px-3 py-2 disabled:opacity-40"
      >
        {busy ? "Generating scenario…" : "Start a practice session →"}
      </button>
    </article>
  );
}
