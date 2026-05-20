/**
 * Screen 1 — Role Select.
 * Centered. Product name + one-line pitch + a role card. Selecting it
 * creates a session (triggers scenario generation server-side) and
 * navigates to /briefing/:sessionId.
 */
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { useStore } from "../state/store";

const ROLES = [
  {
    id: "Junior Full-Stack Developer",
    title: "Junior Full-Stack Developer",
    blurb:
      "First day at a small B2B SaaS startup. One Python API endpoint, an under-specified spec, and a PM who'll change their mind.",
    available: true,
  },
  {
    id: "Product Manager",
    title: "Product Manager",
    blurb: "Coming soon.",
    available: false,
  },
  {
    id: "Data Analyst",
    title: "Data Analyst",
    blurb: "Coming soon.",
    available: false,
  },
] as const;

export default function RoleSelect() {
  const navigate = useNavigate();
  const createSession = useStore((s) => s.createSession);
  const reset = useStore((s) => s.reset);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const onSelect = async (role: string) => {
    reset();
    setBusy(role);
    setError(null);
    try {
      const sid = await createSession(role);
      navigate(`/briefing/${sid}`);
    } catch (e) {
      setError((e as Error).message);
      setBusy(null);
    }
  };

  return (
    <main className="min-h-screen flex items-center justify-center p-8">
      <div className="max-w-3xl w-full space-y-8">
        <header className="text-center space-y-2">
          <h1 className="text-4xl font-semibold tracking-tight text-fg">Day One</h1>
          <p className="text-muted text-lg">Don't interview people. Watch them work.</p>
        </header>

        <section className="grid gap-3" aria-label="Roles">
          {ROLES.map((r) => {
            const isBusy = busy === r.id;
            const disabled = !r.available || busy !== null;
            return (
              <button
                key={r.id}
                type="button"
                onClick={() => onSelect(r.id)}
                disabled={disabled}
                className={[
                  "text-left rounded-lg border p-5 transition-colors w-full",
                  r.available
                    ? "border-border bg-surface hover:bg-surface-2 hover:border-accent/60"
                    : "border-border/40 bg-surface/40 opacity-50 cursor-not-allowed",
                  isBusy ? "ring-2 ring-accent" : "",
                ].join(" ")}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-xs uppercase tracking-wider text-faint mb-1">Role</p>
                    <h2 className="text-xl font-medium text-fg">{r.title}</h2>
                  </div>
                  {isBusy && (
                    <span className="text-xs text-accent">generating scenario…</span>
                  )}
                </div>
                <p className="text-sm text-muted mt-2 leading-relaxed">{r.blurb}</p>
              </button>
            );
          })}
        </section>

        {error && (
          <p className="text-center text-sm text-danger" role="alert">
            {error}
          </p>
        )}

        <footer className="text-center text-xs text-faint">
          AI use during the session is allowed. We measure judgment, not memorization.
        </footer>
      </div>
    </main>
  );
}
