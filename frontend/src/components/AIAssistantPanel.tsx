/**
 * Right rail — the AI assistant (Format A only; not rendered for Format B).
 *
 * Visually distinct from cast channels — "this is the AI helper; using it is
 * allowed." Each turn POSTs to /sessions/{id}/assistant which logs the query
 * and response, feeding the AI-Use rubric.
 */
import { useEffect, useRef, useState } from "react";

import { useStore } from "../state/store";

export default function AIAssistantPanel() {
  const turns = useStore((s) => s.assistantTurns);
  const pending = useStore((s) => s.assistantPending);
  const send = useStore((s) => s.sendAssistantQuery);
  const status = useStore((s) => s.status);
  const [draft, setDraft] = useState("");
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [turns, pending]);

  const submit = async () => {
    const q = draft.trim();
    if (!q || pending) return;
    setDraft("");
    await send(q);
  };

  const disabled = status !== "active";

  return (
    <section className="flex flex-col h-full">
      <header className="px-3 py-2 border-b border-border bg-surface-2/80">
        <p className="text-sm text-fg flex items-center gap-2">
          <span aria-hidden>🤖</span>
          <span>AI Assistant</span>
        </p>
        <p className="text-[11px] text-faint mt-0.5">
          Yours to use. Every turn is logged. We score quality of use, not presence.
        </p>
      </header>

      <div ref={scrollRef} className="flex-1 min-h-0 overflow-y-auto p-3 space-y-3">
        {turns.length === 0 && (
          <p className="text-xs text-faint italic">
            Ask anything — "how do I…", "review this snippet", "edge cases I might miss".
          </p>
        )}
        {turns.map((t, i) => (
          <div
            key={i}
            className={`rounded-md text-sm whitespace-pre-wrap px-3 py-2 ${
              t.role === "user"
                ? "bg-accent/10 border border-accent/30 text-fg"
                : "bg-surface border border-border text-fg"
            }`}
          >
            <p className="text-[10px] uppercase tracking-wider text-faint mb-1">
              {t.role === "user" ? "you" : "assistant"}
            </p>
            <p className="leading-relaxed">{t.content}</p>
          </div>
        ))}
        {pending && (
          <div className="rounded-md bg-surface border border-border px-3 py-2 text-sm text-faint">
            <span className="inline-flex gap-1" aria-label="thinking">
              <span className="w-1 h-1 bg-muted rounded-full animate-pulse" />
              <span className="w-1 h-1 bg-muted rounded-full animate-pulse [animation-delay:120ms]" />
              <span className="w-1 h-1 bg-muted rounded-full animate-pulse [animation-delay:240ms]" />
            </span>
          </div>
        )}
      </div>

      <form
        className="border-t border-border bg-surface-2/80 p-2 flex flex-col gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          void submit();
        }}
      >
        <textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
              e.preventDefault();
              void submit();
            }
          }}
          disabled={disabled || pending}
          rows={3}
          placeholder={disabled ? "Start the session to chat." : "Ask the assistant…"}
          className="w-full bg-bg border border-border rounded-md px-3 py-2 text-sm placeholder:text-faint focus:outline-none focus:border-accent disabled:opacity-50 resize-none font-sans"
        />
        <div className="flex items-center justify-between">
          <span className="text-[10px] text-faint">⌘/Ctrl + Enter</span>
          <button
            type="submit"
            disabled={disabled || pending || !draft.trim()}
            className="rounded-md bg-accent text-black text-sm font-medium px-3 py-1.5 disabled:opacity-40"
          >
            Ask
          </button>
        </div>
      </form>
    </section>
  );
}
