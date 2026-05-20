/**
 * Screen 2 — Briefing.
 * Calm, centered. Shows the generated company + role + tasks brief.
 * "Start your day" → POST /start → /workspace/:sessionId.
 */
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { useStore } from "../state/store";

export default function Briefing() {
  const { sessionId = "" } = useParams();
  const navigate = useNavigate();
  const scenario = useStore((s) => s.scenario);
  const status = useStore((s) => s.status);
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
      <main className="min-h-screen flex items-center justify-center p-8">
        <p className="text-danger text-sm">{error}</p>
      </main>
    );
  }

  if (!scenario) {
    return (
      <main className="min-h-screen flex items-center justify-center p-8">
        <p className="text-muted text-sm">Generating scenario…</p>
      </main>
    );
  }

  return (
    <main className="min-h-screen flex items-center justify-center p-8">
      <div className="max-w-2xl w-full space-y-8">
        <header className="space-y-2">
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

        <section className="space-y-3">
          <p className="text-xs uppercase tracking-wider text-faint">Today's tasks</p>
          <ol className="space-y-3">
            {scenario.tasks.map((t, i) => (
              <li
                key={t.id}
                className="rounded-md border border-border bg-surface/50 p-4"
              >
                <p className="text-sm text-fg">
                  <span className="text-faint mr-2">{i + 1}.</span>
                  <span className="font-medium">{t.title}</span>
                </p>
                <p className="text-xs text-muted mt-1 leading-relaxed">
                  {t.description}
                </p>
              </li>
            ))}
          </ol>
        </section>

        <section className="space-y-3">
          <p className="text-xs uppercase tracking-wider text-faint">Your team</p>
          <ul className="grid grid-cols-3 gap-3">
            {(["pm", "reviewer", "teammate"] as const).map((ch) => {
              const p = scenario.cast[ch];
              return (
                <li
                  key={ch}
                  className="rounded-md border border-border bg-surface/50 p-3"
                >
                  <p className="text-[10px] uppercase tracking-wider text-faint">
                    #{ch}
                  </p>
                  <p className="text-sm text-fg mt-1">{p.name}</p>
                  <p className="text-xs text-muted">{p.role}</p>
                </li>
              );
            })}
          </ul>
        </section>

        <div className="flex justify-center pt-4">
          <button
            type="button"
            onClick={onStart}
            disabled={starting || status === "complete"}
            className="rounded-md bg-accent text-black text-base font-medium px-6 py-2.5 hover:bg-accent-hover transition-colors disabled:opacity-40"
          >
            {starting ? "Starting…" : "Start your day →"}
          </button>
        </div>
      </div>
    </main>
  );
}
