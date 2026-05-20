/**
 * Screen 3 — Workspace (the core screen).
 *
 * Top bar:   task brief | timer | finish
 * Left:      ChannelList + active ChatChannel
 * Center:    Monaco WorkSurface
 * Right:     AI Assistant panel
 *
 * On mount: load session, open WS. On unmount: close WS.
 */
import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import AIAssistantPanel from "../components/AIAssistantPanel";
import ChannelList from "../components/ChannelList";
import ChatChannel from "../components/ChatChannel";
import TaskBrief from "../components/TaskBrief";
import Timer from "../components/Timer";
import WorkSurface from "../components/WorkSurface";
import { useStore } from "../state/store";
import type { Channel } from "../types";

export default function Workspace() {
  const { sessionId = "" } = useParams();
  const navigate = useNavigate();
  const scenario = useStore((s) => s.scenario);
  const status = useStore((s) => s.status);
  const channels = useStore((s) => s.channels);
  const activeChannel = useStore((s) => s.activeChannel);
  const typing = useStore((s) => s.typing);
  const wsState = useStore((s) => s.wsState);
  const startedAt = useStore((s) => s.startedAt);
  const lastError = useStore((s) => s.lastError);
  const loadSession = useStore((s) => s.loadSession);
  const connectWS = useStore((s) => s.connectWS);
  const disconnectWS = useStore((s) => s.disconnectWS);
  const setActiveChannel = useStore((s) => s.setActiveChannel);
  const sendMessage = useStore((s) => s.sendMessage);
  const finishSession = useStore((s) => s.finishSession);

  const [finishing, setFinishing] = useState(false);
  // Track the index of the last message the candidate has "seen" per channel.
  const [seen, setSeen] = useState<Record<Channel, number>>({
    pm: 0,
    reviewer: 0,
    teammate: 0,
  });

  // Load session + open WS on mount.
  useEffect(() => {
    if (!sessionId) return;
    void loadSession(sessionId).then(() => connectWS(sessionId));
    return () => disconnectWS();
  }, [sessionId, loadSession, connectWS, disconnectWS]);

  // Mark active channel as fully seen on switch / new message.
  useEffect(() => {
    setSeen((s) => ({ ...s, [activeChannel]: channels[activeChannel].length }));
  }, [activeChannel, channels]);

  const unread = useMemo(() => {
    return {
      pm: Math.max(0, channels.pm.length - seen.pm),
      reviewer: Math.max(0, channels.reviewer.length - seen.reviewer),
      teammate: Math.max(0, channels.teammate.length - seen.teammate),
    };
  }, [channels, seen]);

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

  return (
    <div className="h-screen grid grid-rows-[var(--layout-topbar)_1fr] bg-bg">
      {/* Top bar */}
      <header className="flex items-center justify-between px-4 border-b border-border bg-surface/80">
        <div className="flex items-center gap-4 min-w-0">
          <TaskBrief scenario={scenario} />
          <span className={`text-[10px] uppercase tracking-wider ${wsBadge}`}>
            ● {wsState}
          </span>
          {lastError && (
            <span className="text-[10px] text-danger truncate" title={lastError}>
              {lastError}
            </span>
          )}
        </div>
        <div className="flex items-center gap-4">
          <Timer startedAt={startedAt} />
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

      {/* Three columns */}
      <div
        className="grid h-full min-h-0"
        style={{
          gridTemplateColumns:
            "var(--layout-channel-rail) 1fr var(--layout-assistant-rail)",
        }}
      >
        {/* LEFT: channels + chat */}
        <aside className="border-r border-border bg-surface grid grid-rows-[auto_1fr] min-h-0">
          <ChannelList
            cast={scenario?.cast ?? null}
            active={activeChannel}
            channels={channels}
            unread={unread}
            onSelect={setActiveChannel}
          />
          <div className="border-t border-border min-h-0">
            <ChatChannel
              channel={activeChannel}
              persona={scenario?.cast[activeChannel]}
              messages={channels[activeChannel]}
              typing={typing[activeChannel]}
              disabled={wsState !== "open" || status !== "active"}
              onSend={sendMessage}
            />
          </div>
        </aside>

        {/* CENTER: work surface */}
        <section className="min-h-0">
          <WorkSurface />
        </section>

        {/* RIGHT: AI assistant */}
        <aside className="border-l border-border bg-surface-2 min-h-0">
          <AIAssistantPanel />
        </aside>
      </div>
    </div>
  );
}
