/**
 * Workspace — the core session screen, format-aware.
 *
 * Format A: top bar | (Channels + Chat) | WorkSurface | AI Assistant
 * Format B: top bar | TaskRail | WorkSurface (no chat, no AI panel)
 *
 * Integrity events captured at this level:
 *  - tab_focus_lost / regained (visibilitychange)
 *  - candidate_pasted_content (paste listener on the workspace)
 */
import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import AIAssistantPanel from "../components/AIAssistantPanel";
import ChannelList from "../components/ChannelList";
import ChatChannel from "../components/ChatChannel";
import FormatBadge from "../components/FormatBadge";
import TaskBrief from "../components/TaskBrief";
import TaskRail from "../components/TaskRail";
import Timer from "../components/Timer";
import WorkSurface from "../components/WorkSurface";
import { useStore } from "../state/store";
import type { Channel } from "../types";

export default function Workspace() {
  const { sessionId = "" } = useParams();
  const navigate = useNavigate();

  // Selectors
  const status = useStore((s) => s.status);
  const format = useStore((s) => s.format);
  const isPractice = useStore((s) => s.isPractice);
  const scenario = useStore((s) => s.scenario);
  const channels = useStore((s) => s.channels);
  const activeChannel = useStore((s) => s.activeChannel);
  const typing = useStore((s) => s.typing);
  const wsState = useStore((s) => s.wsState);
  const lastError = useStore((s) => s.lastError);

  // Actions
  const loadSession = useStore((s) => s.loadSession);
  const connectWS = useStore((s) => s.connectWS);
  const disconnectWS = useStore((s) => s.disconnectWS);
  const setActiveChannel = useStore((s) => s.setActiveChannel);
  const sendMessage = useStore((s) => s.sendMessage);
  const finishSession = useStore((s) => s.finishSession);
  const logTabFocus = useStore((s) => s.logTabFocus);
  const logPaste = useStore((s) => s.logPaste);

  const [finishing, setFinishing] = useState(false);
  const [seen, setSeen] = useState<Record<Channel, number>>({
    pm: 0,
    reviewer: 0,
    peer: 0,
  });

  // Load session + open WS (Format A only) on mount.
  useEffect(() => {
    if (!sessionId) return;
    let cancelled = false;
    void loadSession(sessionId).then(() => {
      if (cancelled) return;
      // Read the latest format from the store (loadSession sets it).
      const fmt = useStore.getState().format;
      if (fmt === "A") connectWS(sessionId);
    });
    return () => {
      cancelled = true;
      disconnectWS();
    };
  }, [sessionId, loadSession, connectWS, disconnectWS]);

  // Visibility / tab-focus integrity events.
  const awaySinceRef = useRef<number | null>(null);
  useEffect(() => {
    const onVis = () => {
      if (status !== "active") return;
      if (document.hidden) {
        awaySinceRef.current = Date.now();
        void logTabFocus("lost");
      } else if (awaySinceRef.current !== null) {
        const away = Date.now() - awaySinceRef.current;
        awaySinceRef.current = null;
        void logTabFocus("regained", away);
      }
    };
    document.addEventListener("visibilitychange", onVis);
    return () => document.removeEventListener("visibilitychange", onVis);
  }, [status, logTabFocus]);

  // Paste-attribution integrity event (workspace-level capture).
  useEffect(() => {
    const onPaste = (ev: ClipboardEvent) => {
      if (status !== "active") return;
      const target = ev.target as HTMLElement | null;
      const where = describePasteTarget(target);
      const text = ev.clipboardData?.getData("text") ?? "";
      const bytes = new Blob([text]).size;
      const preview = text.slice(0, 280);
      // We don't reliably know if a paste came from outside the app vs. an
      // internal copy. Mark "unknown" — never adjudicate from this signal.
      void logPaste(where, bytes, "unknown", preview);
    };
    window.addEventListener("paste", onPaste);
    return () => window.removeEventListener("paste", onPaste);
  }, [status, logPaste]);

  // Mark active channel as fully seen on switch / new message.
  useEffect(() => {
    setSeen((s) => ({ ...s, [activeChannel]: channels[activeChannel].length }));
  }, [activeChannel, channels]);

  const unread = useMemo(
    () => ({
      pm: Math.max(0, channels.pm.length - seen.pm),
      reviewer: Math.max(0, channels.reviewer.length - seen.reviewer),
      peer: Math.max(0, channels.peer.length - seen.peer),
    }),
    [channels, seen],
  );

  const onFinish = async () => {
    if (!sessionId) return;
    const ok = window.confirm(
      "Finish your day? The session ends and evaluators score what they saw. This may take ~20–30 seconds.",
    );
    if (!ok) return;
    setFinishing(true);
    try {
      await finishSession();
      navigate(`/scorecard/${sessionId}`);
    } catch (e) {
      window.alert(`Could not end session: ${(e as Error).message}`);
      setFinishing(false);
    }
  };

  const wsBadge =
    wsState === "open"
      ? "text-success"
      : wsState === "connecting"
        ? "text-warning"
        : "text-faint";

  const isA = format === "A";

  return (
    <div className="h-screen grid grid-rows-[var(--layout-topbar)_1fr] bg-bg">
      {/* Top bar */}
      <header className="flex items-center justify-between px-4 border-b border-border bg-surface/80">
        <div className="flex items-center gap-4 min-w-0">
          <FormatBadge format={format} practice={isPractice} />
          <TaskBrief scenario={scenario} />
          {isA && (
            <span className={`text-[10px] uppercase tracking-wider ${wsBadge}`}>
              ● {wsState}
            </span>
          )}
          {lastError && (
            <span className="text-[10px] text-danger truncate" title={lastError}>
              {lastError}
            </span>
          )}
        </div>
        <div className="flex items-center gap-4">
          <Timer />
          <button
            type="button"
            onClick={onFinish}
            disabled={finishing || status !== "active"}
            className="rounded-md bg-accent text-black text-sm font-medium px-3 py-1.5 hover:bg-accent-hover disabled:opacity-40"
          >
            {finishing ? "Scoring…" : "Finish"}
          </button>
        </div>
      </header>

      {/* Body */}
      {isA ? <FormatALayout unread={unread} setActiveChannel={setActiveChannel}
                activeChannel={activeChannel} channels={channels} typing={typing}
                wsState={wsState} status={status} sendMessage={sendMessage} /> :
        <FormatBLayout />}
    </div>
  );
}

function describePasteTarget(
  target: HTMLElement | null,
): "work_surface" | "chat" | "assistant" {
  if (!target) return "work_surface";
  const inside = (sel: string) => !!target.closest(sel);
  if (inside('[data-surface="assistant"]')) return "assistant";
  if (inside('[data-surface="chat"]')) return "chat";
  return "work_surface";
}

// ----- Format A layout (cast + code + assistant) -----

function FormatALayout(props: {
  unread: Record<Channel, number>;
  setActiveChannel: (c: Channel) => void;
  activeChannel: Channel;
  channels: Record<Channel, import("../types").ChatMessage[]>;
  typing: Record<Channel, boolean>;
  wsState: "closed" | "connecting" | "open";
  status: import("../types").SessionStatus | "idle";
  sendMessage: (content: string) => void;
}) {
  const scenario = useStore((s) => s.scenario);
  return (
    <div
      className="grid h-full min-h-0"
      style={{
        gridTemplateColumns:
          "var(--layout-channel-rail) 1fr var(--layout-assistant-rail)",
      }}
    >
      <aside
        data-surface="chat"
        className="border-r border-border bg-surface grid grid-rows-[auto_1fr] min-h-0"
      >
        <ChannelList
          cast={scenario && "cast" in scenario ? scenario.cast : null}
          active={props.activeChannel}
          channels={props.channels}
          unread={props.unread}
          onSelect={props.setActiveChannel}
        />
        <div className="border-t border-border min-h-0">
          <ChatChannel
            channel={props.activeChannel}
            persona={
              scenario && "cast" in scenario
                ? scenario.cast[props.activeChannel]
                : undefined
            }
            messages={props.channels[props.activeChannel]}
            typing={props.typing[props.activeChannel]}
            disabled={props.wsState !== "open" || props.status !== "active"}
            onSend={props.sendMessage}
          />
        </div>
      </aside>

      <section className="min-h-0">
        <WorkSurface />
      </section>

      <aside
        data-surface="assistant"
        className="border-l border-border bg-surface-2 min-h-0"
      >
        <AIAssistantPanel />
      </aside>
    </div>
  );
}

// ----- Format B layout (task list + code, no chat, no AI panel) -----

function FormatBLayout() {
  return (
    <div
      className="grid h-full min-h-0"
      style={{ gridTemplateColumns: "var(--layout-task-rail) 1fr" }}
    >
      <aside className="border-r border-border bg-surface min-h-0">
        <TaskRail />
      </aside>
      <section className="min-h-0">
        <WorkSurface />
      </section>
    </div>
  );
}
