/**
 * Disclosure — the pre-session candidate notice (§3.2, §11.3).
 *
 * Plain-language, format-specific. Candidates must explicitly acknowledge
 * before clicking through to the Briefing. Offers the alternative-assessment
 * path. Surfaces accessibility opt-in.
 */
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import AccessibilityToggle from "../components/AccessibilityToggle";
import FormatBadge from "../components/FormatBadge";
import { useStore } from "../state/store";

export default function Disclosure() {
  const { sessionId = "" } = useParams();
  const navigate = useNavigate();
  const loadSession = useStore((s) => s.loadSession);
  const format = useStore((s) => s.format);
  const isPractice = useStore((s) => s.isPractice);
  const minutes = useStore((s) => s.sessionMinutes);
  const storeSessionId = useStore((s) => s.sessionId);
  const role = useStore((s) => s.scenario?.role ?? null);
  const [ack, setAck] = useState(false);
  const [showAlt, setShowAlt] = useState(false);

  useEffect(() => {
    if (sessionId && storeSessionId !== sessionId) {
      loadSession(sessionId).catch(() => undefined);
    }
  }, [sessionId, storeSessionId, loadSession]);

  const isA = format === "A";

  return (
    <main id="main" className="max-w-3xl mx-auto px-4 py-10 space-y-8">
      <header className="space-y-2">
        <p className="text-xs uppercase tracking-wider text-faint">
          Before you begin
        </p>
        <h1 className="text-3xl font-semibold tracking-tight text-fg">
          What this assessment is — and what it isn't
        </h1>
        <div className="flex flex-wrap items-center gap-2 pt-2">
          <FormatBadge format={format} size="md" practice={isPractice} />
          <span className="text-xs text-muted">
            {role ?? "—"} · {minutes} minutes
          </span>
        </div>
      </header>

      <section className="rounded-lg border border-border bg-surface p-5 space-y-3">
        <p className="text-xs uppercase tracking-wider text-faint">
          Automated Employment Decision Tool
        </p>
        <p className="text-sm text-muted leading-relaxed">
          Day One is an AEDT under NYC Local Law 144 and a high-risk AI system
          under the EU AI Act (Annex III §4). The hiring company has chosen to
          use Day One for this stage of their process. A human reviewer at the
          hiring company makes any hire decision; our customer license forbids
          them from automating that decision based solely on this scorecard.
        </p>
      </section>

      <section className="rounded-lg border border-border bg-surface p-5 space-y-3">
        <p className="text-xs uppercase tracking-wider text-faint">
          What you'll do
        </p>
        {isA ? (
          <>
            <p className="text-sm text-muted leading-relaxed">
              You'll join a fictional company as a new team member. You'll
              Slack with a PM, a reviewer, and a peer. You'll work in a code
              editor on a small, deliberately under-specified set of tasks.
              The PM may change a requirement mid-session — that's expected.
            </p>
            <p className="text-sm text-muted leading-relaxed">
              <strong className="text-fg">AI use is allowed and expected.</strong>{" "}
              An AI assistant is built into the work surface. Use it. We score
              the <em>quality</em> of your AI use — not its presence.
            </p>
          </>
        ) : (
          <>
            <p className="text-sm text-muted leading-relaxed">
              You'll work alone in a code editor on a set of 2–3 coding tasks
              with visible tests and additional hidden tests that run when you
              submit. No chat, no AI assistant available in the work surface.
            </p>
            <p className="text-sm text-muted leading-relaxed">
              <strong className="text-fg">AI is not available here.</strong>{" "}
              The work surface does not provide an AI helper. We do not
              attempt to detect AI use on your separate devices; we trust the
              format restriction itself plus the integrity context we capture.
            </p>
          </>
        )}
      </section>

      <section className="rounded-lg border border-border bg-surface p-5 space-y-3">
        <p className="text-xs uppercase tracking-wider text-faint">
          What we record
        </p>
        <ul className="text-sm text-muted leading-relaxed list-disc pl-5 space-y-1">
          <li>Every chat message you send, and every cast reply.</li>
          <li>Every snapshot of your code as you edit it.</li>
          {isA && <li>Every question to and response from the AI assistant.</li>}
          <li>
            Tab focus changes and paste events — surfaced as context, never
            scored.
          </li>
          <li>
            <strong className="text-fg">No webcam, no keystroke biometrics, no mouse biometrics.</strong>{" "}
            See §6 of our product spec.
          </li>
        </ul>
      </section>

      <section className="rounded-lg border border-border bg-surface p-5 space-y-3">
        <p className="text-xs uppercase tracking-wider text-faint">
          Your rights during and after
        </p>
        <ul className="text-sm text-muted leading-relaxed space-y-2">
          <li>
            · You can request an{" "}
            <button
              type="button"
              onClick={() => setShowAlt((v) => !v)}
              className="text-accent underline-offset-2 hover:underline"
            >
              alternative assessment process
            </button>
            .
          </li>
          <li>· You'll receive the same scorecard the recruiter sees.</li>
          <li>
            · You can request human review of your scorecard within 14 days.
          </li>
          <li>· You can request a copy of, or deletion of, your session data.</li>
        </ul>
        {showAlt && (
          <div className="rounded-md bg-surface-2 border border-border p-3 text-sm text-muted leading-relaxed">
            <p>
              If you'd prefer a human-administered work-sample assessment
              instead of this Day One session, click "Request alternative
              assessment" below. We'll route the request to the hiring company's
              recruiting team. Day One does not invent the alternative — your
              employer's existing process is the alternative.
            </p>
            <button
              type="button"
              className="mt-2 text-xs px-3 py-1.5 rounded-md border border-border text-fg hover:border-accent"
              onClick={() => alert("Request routed to the hiring company.")}
            >
              Request alternative assessment
            </button>
          </div>
        )}
      </section>

      <section className="rounded-lg border border-border bg-surface p-5 space-y-3">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs uppercase tracking-wider text-faint">
              Accessibility Mode
            </p>
            <p className="text-sm text-muted leading-relaxed mt-1">
              Self-elected. No documentation required. Extended time does not
              affect your scorecard. Open the panel anytime from the top-right
              menu during the session.
            </p>
          </div>
          <AccessibilityToggle />
        </div>
      </section>

      <section className="rounded-lg border border-accent/40 bg-accent-soft/30 p-5 space-y-3">
        <label className="flex items-start gap-3 cursor-pointer">
          <input
            type="checkbox"
            className="mt-1 accent-accent"
            checked={ack}
            onChange={(e) => setAck(e.target.checked)}
          />
          <span className="text-sm text-fg leading-relaxed">
            I've read the above. I understand Day One is decision-support for a
            human reviewer at the hiring company. I consent to the recording
            described above.
          </span>
        </label>
        <div className="flex items-center justify-between pt-1">
          <button
            type="button"
            onClick={() => navigate("/")}
            className="text-sm text-muted hover:text-fg"
          >
            ← Back
          </button>
          <button
            type="button"
            disabled={!ack}
            onClick={() => navigate(`/briefing/${sessionId}`)}
            className="rounded-md bg-accent text-black text-sm font-medium px-4 py-2 disabled:opacity-40"
          >
            Continue to briefing →
          </button>
        </div>
      </section>
    </main>
  );
}
