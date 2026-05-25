/**
 * Active channel's conversation: message thread + typing indicator + input.
 * Three message kinds:
 *   - "candidate"           → right-aligned bubble
 *   - "agent"               → left-aligned with actor_name
 *   - "requirement_change"  → full-width inline notification (warning accent)
 */
import { useEffect, useRef, useState } from "react";

import type { Channel, ChatMessage, Persona } from "../types";

interface Props {
  channel: Channel;
  persona: Persona | undefined;
  messages: ChatMessage[];
  typing: boolean;
  disabled: boolean;
  onSend: (content: string) => void;
}

function fmtTs(ms: number): string {
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  return `${m}:${(s % 60).toString().padStart(2, "0")}`;
}

export default function ChatChannel({
  channel,
  persona,
  messages,
  typing,
  disabled,
  onSend,
}: Props) {
  const [draft, setDraft] = useState("");
  const scrollRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, typing]);

  const submit = () => {
    if (!draft.trim()) return;
    onSend(draft);
    setDraft("");
  };

  return (
    <div className="flex flex-col h-full" data-surface="chat">
      <header className="px-3 py-2 border-b border-border bg-surface/60">
        <p className="text-sm text-fg">
          <span className="text-faint">#</span>
          {channel}
          {persona && (
            <span className="ml-2 text-xs text-muted">
              · {persona.name} ({persona.role})
            </span>
          )}
        </p>
      </header>

      <div ref={scrollRef} className="flex-1 min-h-0 overflow-y-auto p-3 space-y-3">
        {messages.length === 0 && (
          <p className="text-xs text-faint italic">
            No messages yet. Say hello to {persona?.name ?? `the ${channel}`}.
          </p>
        )}
        {messages.map((m, i) => {
          if (m.kind === "requirement_change") {
            return (
              <div
                key={i}
                className="rounded-md border border-warning/60 bg-warning/10 px-3 py-2 text-sm"
              >
                <p className="text-xs uppercase tracking-wider text-warning mb-1 flex items-center gap-2">
                  <span>⚡</span>
                  <span>Requirement change</span>
                  <span className="text-faint normal-case font-normal">
                    · {m.actor_name} · {fmtTs(m.ts_ms)}
                  </span>
                </p>
                <p className="text-fg leading-relaxed whitespace-pre-wrap">{m.content}</p>
              </div>
            );
          }
          const isCandidate = m.kind === "candidate";
          return (
            <div
              key={i}
              className={`flex ${isCandidate ? "justify-end" : "justify-start"}`}
            >
              <div
                className={[
                  "max-w-[80%] rounded-md px-3 py-2 text-sm whitespace-pre-wrap",
                  isCandidate
                    ? "bg-accent/15 border border-accent/40 text-fg"
                    : "bg-surface-2 border border-border text-fg",
                ].join(" ")}
              >
                {!isCandidate && m.actor_name && (
                  <p className="text-xs text-faint mb-1">
                    {m.actor_name} · {fmtTs(m.ts_ms)}
                  </p>
                )}
                <p className="leading-relaxed">{m.content}</p>
                {isCandidate && (
                  <p className="text-[10px] text-faint mt-1 text-right">{fmtTs(m.ts_ms)}</p>
                )}
              </div>
            </div>
          );
        })}
        {typing && (
          <div className="flex justify-start">
            <div className="rounded-md px-3 py-2 text-sm bg-surface-2 border border-border text-faint">
              <span className="inline-flex gap-1" aria-label="typing">
                <span className="w-1 h-1 bg-muted rounded-full animate-pulse" />
                <span className="w-1 h-1 bg-muted rounded-full animate-pulse [animation-delay:120ms]" />
                <span className="w-1 h-1 bg-muted rounded-full animate-pulse [animation-delay:240ms]" />
              </span>
            </div>
          </div>
        )}
      </div>

      <form
        className="border-t border-border bg-surface/60 p-2 flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
        <input
          type="text"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          disabled={disabled}
          placeholder={disabled ? "connecting…" : `Message ${persona?.name ?? `#${channel}`}…`}
          className="flex-1 bg-bg border border-border rounded-md px-3 py-1.5 text-sm placeholder:text-faint focus:outline-none focus:border-accent disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={disabled || !draft.trim()}
          className="rounded-md bg-accent text-black text-sm font-medium px-3 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Send
        </button>
      </form>
    </div>
  );
}
