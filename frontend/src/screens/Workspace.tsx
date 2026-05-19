/**
 * Screen 3 — Workspace (the core screen).
 * Three-column layout + top bar:
 *   top bar — task brief (collapsible) | timer | Finish
 *   left   — ChannelList + active ChatChannel (#pm, #reviewer, #teammate)
 *   center — Monaco work surface
 *   right  — AI Assistant panel (clearly delineated; usage is explicitly allowed)
 *
 * Wired to the backend (REST + WS) in Phase 6.
 */
export default function Workspace() {
  return (
    <div className="h-screen grid grid-rows-[var(--layout-topbar)_1fr]">
      <header className="flex items-center justify-between px-4 border-b border-[var(--color-border)] bg-[var(--color-surface)]">
        <span className="text-sm text-[var(--color-muted)]">Task brief (collapsible)</span>
        <span className="text-sm font-mono text-[var(--color-fg)]">--:--</span>
        <button
          type="button"
          className="text-sm px-3 py-1.5 rounded-[var(--radius-md)] bg-[var(--color-accent)] text-black font-medium opacity-60 cursor-not-allowed"
          disabled
        >
          Finish
        </button>
      </header>

      <div
        className="grid h-full min-h-0"
        style={{
          gridTemplateColumns:
            "var(--layout-channel-rail) 1fr var(--layout-assistant-rail)",
        }}
      >
        <aside className="border-r border-[var(--color-border)] bg-[var(--color-surface)] p-3 text-sm text-[var(--color-muted)]">
          Channels / chat (Phase 6)
        </aside>

        <section className="bg-[var(--color-bg)] p-3 text-sm text-[var(--color-muted)]">
          Monaco work surface (Phase 6)
        </section>

        <aside className="border-l border-[var(--color-border)] bg-[var(--color-surface-2)] p-3 text-sm text-[var(--color-muted)]">
          AI Assistant (Phase 6)
        </aside>
      </div>
    </div>
  );
}
