/**
 * Landing — the v3 candidate entry point.
 *
 * Composition: hero pitch + Format A vs Format B comparison cards + role
 * picker + AEDT/compliance signal + Practice Mode link + ComplianceFooter.
 */
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import ComplianceFooter from "../components/ComplianceFooter";
import FormatBadge from "../components/FormatBadge";
import { useStore } from "../state/store";
import type { SessionFormat } from "../types";

const ROLES = [
  {
    id: "Junior Full-Stack Developer",
    title: "Junior Full-Stack Developer",
    formats: ["A", "B"] as SessionFormat[],
    blurb:
      "First day at a small B2B SaaS startup. A Python API endpoint, an under-specified spec, and a planned mid-session twist.",
  },
  {
    id: "Mid-level Backend Engineer",
    title: "Mid-level Backend Engineer",
    formats: ["A", "B"] as SessionFormat[],
    blurb:
      "Service refactor + small feature. The PM will shift priorities on you. Reviewer is opinionated about the codebase.",
  },
  {
    id: "Platform Engineer",
    title: "Platform Engineer",
    formats: ["A", "B"] as SessionFormat[],
    blurb:
      "Operational reliability scenario. Tradeoffs visible. Decide what to ship, what to defer.",
  },
];

export default function Landing() {
  const navigate = useNavigate();
  const createSession = useStore((s) => s.createSession);
  const reset = useStore((s) => s.reset);
  const accessibility = useStore((s) => s.accessibility);

  const [format, setFormat] = useState<SessionFormat>("A");
  const [minutes, setMinutes] = useState<number>(60);
  const [candidateLabel, setCandidateLabel] = useState<string>("");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const onSelect = async (roleId: string) => {
    reset();
    setBusy(roleId);
    setError(null);
    try {
      const sid = await createSession({
        role: roleId,
        format,
        session_minutes: minutes,
        candidate_label: candidateLabel.trim() || null,
        accessibility,
      });
      navigate(`/disclosure/${sid}`);
    } catch (e) {
      setError((e as Error).message);
      setBusy(null);
    }
  };

  return (
    <>
      <main id="main" className="max-w-6xl mx-auto px-4 pt-12 pb-20 space-y-16">
        {/* Hero */}
        <header className="text-center space-y-4 max-w-3xl mx-auto">
          <p className="text-xs uppercase tracking-wider text-faint">
            A work-assessment platform for technical hiring
          </p>
          <h1 className="text-5xl font-semibold tracking-tight text-fg">
            Don't interview people.
            <br />
            <span className="text-accent">Watch them work.</span>
          </h1>
          <p className="text-muted leading-relaxed text-lg">
            Day One drops a candidate into a 60-minute realistic-work session
            at a fictional company. AI-resistant by design. Evidence-cited
            scorecard. Decision support — never a verdict.
          </p>
        </header>

        {/* Format comparison */}
        <section aria-label="Choose a format" className="space-y-4">
          <div className="flex items-baseline justify-between flex-wrap gap-2">
            <h2 className="text-xs uppercase tracking-wider text-faint">
              Step 1 · Choose a format
            </h2>
            <p className="text-xs text-faint">
              You can switch later from the candidate flow.
            </p>
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            <FormatCard
              format="A"
              active={format === "A"}
              onClick={() => setFormat("A")}
            />
            <FormatCard
              format="B"
              active={format === "B"}
              onClick={() => setFormat("B")}
            />
          </div>
        </section>

        {/* Session config */}
        <section className="rounded-xl border border-border bg-surface p-5 space-y-4">
          <h2 className="text-xs uppercase tracking-wider text-faint">
            Step 2 · Session configuration
          </h2>
          <div className="grid sm:grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-muted mb-1 block">
                Session length (band: 30–90 min)
              </label>
              <div className="flex gap-1">
                {[30, 45, 60, 75, 90].map((m) => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => setMinutes(m)}
                    className={`flex-1 text-sm py-2 rounded-md border ${
                      minutes === m
                        ? "border-accent text-accent bg-accent-soft/40"
                        : "border-border text-muted hover:text-fg"
                    }`}
                  >
                    {m}m
                  </button>
                ))}
              </div>
              <p className="text-[10px] text-faint mt-1.5">
                Default 60 minutes per v3 §2.2. Accessibility Mode extended-time
                multiplier applies on top.
              </p>
            </div>
            <div>
              <label htmlFor="cand" className="text-xs text-muted mb-1 block">
                Candidate label <span className="text-faint">(optional, demo only)</span>
              </label>
              <input
                id="cand"
                type="text"
                value={candidateLabel}
                onChange={(e) => setCandidateLabel(e.target.value)}
                placeholder="e.g. Demo for HackIndia judges"
                maxLength={120}
                className="w-full bg-bg border border-border rounded-md px-3 py-2 text-sm placeholder:text-faint focus:outline-none focus:border-accent"
              />
              <p className="text-[10px] text-faint mt-1.5">
                Surfaces in the recruiter dashboard. Never seen by evaluators.
              </p>
            </div>
          </div>
        </section>

        {/* Role picker */}
        <section className="space-y-4">
          <h2 className="text-xs uppercase tracking-wider text-faint">
            Step 3 · Pick a role to start
          </h2>
          <div className="grid gap-3">
            {ROLES.map((r) => {
              const supported = r.formats.includes(format);
              const isBusy = busy === r.id;
              return (
                <button
                  key={r.id}
                  type="button"
                  disabled={!supported || busy !== null}
                  onClick={() => onSelect(r.id)}
                  className={`text-left rounded-lg border p-5 transition-colors w-full ${
                    supported
                      ? "border-border bg-surface hover:bg-surface-2 hover:border-accent/60"
                      : "border-border/40 bg-surface/40 opacity-50 cursor-not-allowed"
                  } ${isBusy ? "ring-2 ring-accent" : ""}`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-xs uppercase tracking-wider text-faint mb-1">
                        Role · Engineering
                      </p>
                      <h3 className="text-xl font-medium text-fg">{r.title}</h3>
                    </div>
                    {isBusy && (
                      <span className="text-xs text-accent shrink-0">
                        generating scenario…
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-muted mt-2 leading-relaxed">{r.blurb}</p>
                </button>
              );
            })}
          </div>
          {error && (
            <p className="text-sm text-danger" role="alert">
              {error}
            </p>
          )}
        </section>

        {/* Practice + recruiter */}
        <section className="grid sm:grid-cols-2 gap-4">
          <Link
            to="/practice"
            className="rounded-lg border border-border bg-surface p-5 hover:border-accent/60 transition-colors"
          >
            <p className="text-xs uppercase tracking-wider text-faint">
              Practice Mode
            </p>
            <p className="text-fg mt-1 font-medium">Try a no-stakes session →</p>
            <p className="text-xs text-muted mt-1.5 leading-relaxed">
              Free, unlimited, scored nowhere. Available in both formats.
            </p>
          </Link>
          <Link
            to="/recruiter"
            className="rounded-lg border border-border bg-surface p-5 hover:border-accent/60 transition-colors"
          >
            <p className="text-xs uppercase tracking-wider text-faint">
              For recruiters
            </p>
            <p className="text-fg mt-1 font-medium">Open the dashboard →</p>
            <p className="text-xs text-muted mt-1.5 leading-relaxed">
              Live + completed sessions, scorecards with the same evidence the
              candidate sees.
            </p>
          </Link>
        </section>
      </main>
      <ComplianceFooter />
    </>
  );
}

function FormatCard({
  format,
  active,
  onClick,
}: {
  format: SessionFormat;
  active: boolean;
  onClick: () => void;
}) {
  const isA = format === "A";
  return (
    <button
      type="button"
      onClick={onClick}
      className={`text-left rounded-xl border p-5 transition-colors space-y-3 ${
        active
          ? "border-accent bg-surface ring-2 ring-accent/40"
          : "border-border bg-surface hover:bg-surface-2 hover:border-border-strong"
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <FormatBadge format={format} size="md" />
        <span
          className={`text-[10px] uppercase tracking-wider ${
            active ? "text-accent" : "text-faint"
          }`}
        >
          {active ? "selected" : "click to select"}
        </span>
      </div>
      <h3 className="text-xl text-fg font-medium">
        {isA ? "Multi-Agent Work Simulation" : "Solo Technical Assessment"}
      </h3>
      <p className="text-sm text-muted leading-relaxed">
        {isA
          ? "Branching scenario with a cast of AI agents (PM, reviewer, peer), a planned mid-session twist, and a built-in AI assistant. AI use is allowed by design — we measure judgment, communication, and quality of AI use."
          : "Code-only, candidate-and-IDE. No cast. No twist. No AI assistant in the work surface. The Day One spine (evidence-cited rubric, accessibility, no biometric anti-cheat, appeal workflow) applied to a controlled coding assessment."}
      </p>
      <ul className="text-xs text-muted space-y-1.5 leading-relaxed">
        {(isA
          ? [
              "Cast agents react in real time",
              "AI assistant available — built-in, logged, scored on QUALITY of use",
              "Planned mid-session twist tests response to change",
              "6 rubric axes",
            ]
          : [
              "Solo work in a sandboxed code editor",
              "No AI assistant in the work surface",
              "Visible + hidden tests; the candidate runs their code",
              "5 rubric axes",
            ]
        ).map((line) => (
          <li key={line}>· {line}</li>
        ))}
      </ul>
    </button>
  );
}
