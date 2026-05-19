/**
 * Screen 1 — Role Select.
 * Centered. Product name + one-line pitch + role cards.
 * Selecting a role creates a session and navigates to Briefing.
 *
 * Wired to the backend in Phase 6.
 */
export default function RoleSelect() {
  return (
    <main className="min-h-screen flex items-center justify-center p-8">
      <div className="max-w-2xl w-full text-center space-y-8">
        <header className="space-y-2">
          <h1 className="text-4xl font-semibold tracking-tight">Day One</h1>
          <p className="text-muted">Don't interview people. Watch them work.</p>
        </header>

        <section className="grid gap-3">
          {/* Role cards land here in Phase 6 — single card today for V1. */}
          <div className="rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6 text-left opacity-70">
            <p className="text-sm uppercase tracking-wider text-[var(--color-faint)]">Role</p>
            <h2 className="text-xl font-medium mt-1">Junior Full-Stack Developer</h2>
            <p className="text-sm text-[var(--color-muted)] mt-2">
              (Phase 6 will wire this card to create a session and route to Briefing.)
            </p>
          </div>
        </section>
      </div>
    </main>
  );
}
