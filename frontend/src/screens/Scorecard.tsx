/**
 * Screen 4 — Scorecard.
 * Decision-support disclaimer (never a verdict) + one ScoreAxis block per
 * rubric axis, each with expandable EvidenceItems showing ts + quote + reasoning.
 *
 * Wired to the backend in Phase 6.
 */
export default function Scorecard() {
  return (
    <main className="min-h-screen p-8 max-w-4xl mx-auto space-y-8">
      <header className="space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight">Scorecard</h1>
        <p className="text-sm text-[var(--color-muted)]">
          Decision support for a human reviewer — not an automated verdict.
        </p>
      </header>
      <p className="text-[var(--color-muted)]">
        (Phase 5 produces the evidence-cited scores; Phase 6 renders them here.)
      </p>
    </main>
  );
}
