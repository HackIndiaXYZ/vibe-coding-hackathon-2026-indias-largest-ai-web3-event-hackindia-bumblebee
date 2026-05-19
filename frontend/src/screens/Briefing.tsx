/**
 * Screen 2 — Briefing.
 * Shows generated company, role, and task brief. Primary "Start" button → Workspace.
 *
 * Wired to the backend in Phase 6.
 */
export default function Briefing() {
  return (
    <main className="min-h-screen flex items-center justify-center p-8">
      <div className="max-w-2xl w-full space-y-6">
        <p className="text-sm uppercase tracking-wider text-[var(--color-faint)]">Briefing</p>
        <h1 className="text-3xl font-semibold tracking-tight">
          (Scenario will load here.)
        </h1>
        <p className="text-[var(--color-muted)]">
          Phase 2 generates the fictional company + task; Phase 6 renders it and wires the Start button.
        </p>
      </div>
    </main>
  );
}
