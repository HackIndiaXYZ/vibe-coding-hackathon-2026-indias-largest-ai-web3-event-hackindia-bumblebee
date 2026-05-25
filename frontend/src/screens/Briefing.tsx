/**
 * Briefing — format-aware.
 *
 * Format A: company + role + tasks + cast.
 * Format B: company + role + tasks (with starter signature + visible tests).
 *
 * Click "Start" → POST /start → /workspace/:sid.
 */
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import FormatBadge from "../components/FormatBadge";
import { useStore } from "../state/store";
import { isFormatA } from "../types";

export default function Briefing() {
  const { sessionId = "" } = useParams();
  const navigate = useNavigate();
  const scenario = useStore((s) => s.scenario);
  const status = useStore((s) => s.status);
  const format = useStore((s) => s.format);
  const minutes = useStore((s) => s.sessionMinutes);
  const isPractice = useStore((s) => s.isPractice);
  const loadSession = useStore((s) => s.loadSession);
  const startSession = useStore((s) => s.startSession);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (sessionId && !scenario) {
      loadSession(sessionId).catch((e) => setError((e as Error).message));
    }
  }, [sessionId, scenario, loadSession]);

  const onStart = async () => {
    setStarting(true);
    setError(null);
    try {
      await startSession();
      navigate(`/workspace/${sessionId}`);
    } catch (e) {
      setError((e as Error).message);
      setStarting(false);
    }
  };

  if (error) {
    return (
      <main id="main" className="min-h-screen flex items-center justify-center p-8">
        <p className="text-danger text-sm">{error}</p>
      </main>
    );
  }
  if (!scenario) {
    return (
      <main id="main" className="min-h-screen flex items-center justify-center p-8">
        <p className="text-muted text-sm">Generating scenario…</p>
      </main>
    );
  }

  return (
    <main id="main" className="max-w-3xl mx-auto px-4 py-10 space-y-8">
      <header className="space-y-2">
        <div className="flex items-center gap-2 flex-wrap">
          <FormatBadge format={format} size="md" practice={isPractice} />
          <span className="text-xs text-muted">· {minutes}-minute session</span>
        </div>
        <p className="text-xs uppercase tracking-wider text-faint">Briefing</p>
        <h1 className="text-3xl font-semibold tracking-tight text-fg">
          {scenario.company_name}
        </h1>
        <p className="text-muted leading-relaxed">{scenario.company_context}</p>
      </header>

      <section className="rounded-lg border border-border bg-surface p-5 space-y-3">
        <p className="text-xs uppercase tracking-wider text-faint">Your role</p>
        <p className="text-lg text-fg">{scenario.role}</p>
        <p className="text-sm text-muted leading-relaxed">
          {scenario.candidate_role_summary}
        </p>
      </section>

      {/* Tasks — shared shape between A and B (B adds visible tests) */}
      <section className="space-y-3">
        <p className="text-xs uppercase tracking-wider text-faint">
          Today's {format === "A" ? "tasks" : "coding tasks"}
        </p>
        <ol className="space-y-3">
          {scenario.tasks.map((t, i) => (
            <li
              key={t.id}
              className="rounded-md border border-border bg-surface/60 p-4 space-y-2"
            >
              <div className="flex items-baseline justify-between gap-3">
                <p className="text-sm text-fg">
                  <span className="text-faint mr-2">{i + 1}.</span>
                  <span className="font-medium">{t.title}</span>
                </p>
                {!isFormatA(scenario) && "expected_minutes" in t && (
                  <span className="text-xs text-faint">
                    ~{(t as { expected_minutes: number }).expected_minutes} min
                  </span>
                )}
              </div>
              <p className="text-xs text-muted leading-relaxed">{t.description}</p>
              {!isFormatA(scenario) && "visible_tests" in t && (
                <details className="text-xs">
                  <summary className="cursor-pointer text-faint hover:text-muted">
                    Visible tests
                  </summary>
                  <pre className="mt-1.5 p-2 bg-bg/60 border border-border rounded text-[11px] text-fg overflow-x-auto font-mono">
                    {(t as { visible_tests: string }).visible_tests}
                  </pre>
                </details>
              )}
            </li>
          ))}
        </ol>
      </section>

      {/* Cast — Format A only */}
      {isFormatA(scenario) && (
        <section className="space-y-3">
          <p className="text-xs uppercase tracking-wider text-faint">Your team</p>
          <ul className="grid grid-cols-3 gap-3">
            {(["pm", "reviewer", "peer"] as const).map((ch) => {
              const p = scenario.cast[ch];
              return (
                <li key={ch} className="rounded-md border border-border bg-surface/60 p-3">
                  <p className="text-[10px] uppercase tracking-wider text-faint">
                    #{ch}
                  </p>
                  <p className="text-sm text-fg mt-1">{p.name}</p>
                  <p className="text-xs text-muted">{p.role}</p>
                </li>
              );
            })}
          </ul>
          <p className="text-[11px] text-faint italic">
            Each persona has a hidden agenda. Inferring it is part of the
            session — it is never displayed.
          </p>
        </section>
      )}

      {/* AI banner — Format-dependent reminder */}
      <section
        className={`rounded-lg border p-4 ${
          format === "A"
            ? "border-format-a/50 bg-format-a/10"
            : "border-format-b/50 bg-format-b/10"
        }`}
      >
        <p className="text-xs uppercase tracking-wider text-faint mb-1">
          AI in this session
        </p>
        <p className="text-sm text-fg leading-relaxed">
          {format === "A"
            ? "An AI assistant is built into the work surface. Use it freely. We score the quality of your use, not its presence."
            : "No AI assistant is available in the work surface. The format restriction itself is the integrity defense; we do not deploy biometric anti-cheat."}
        </p>
      </section>

      <div className="flex justify-between items-center pt-4">
        <button
          type="button"
          onClick={() => navigate(`/disclosure/${sessionId}`)}
          className="text-sm text-muted hover:text-fg"
        >
          ← Back to disclosure
        </button>
        <button
          type="button"
          onClick={onStart}
          disabled={starting || status === "complete"}
          className="rounded-md bg-accent text-black text-base font-medium px-6 py-2.5 hover:bg-accent-hover transition-colors disabled:opacity-40"
        >
          {starting ? "Starting…" : "Start your day →"}
        </button>
      </div>
    </main>
  );
}
