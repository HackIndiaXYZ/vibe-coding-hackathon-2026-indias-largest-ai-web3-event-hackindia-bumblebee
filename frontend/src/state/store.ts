/**
 * Global session store (Zustand).
 *
 * Holds everything the screens need: active sessionId, scenario, channel
 * messages, work-surface content, assistant transcript, WS connection,
 * scorecard. Screens subscribe via `useStore(selector)`.
 */
import { create } from "zustand";

import { api } from "../api/client";
import { openSessionSocket, sendCandidateMessage } from "../api/ws";
import type {
  AssistantTurn,
  Channel,
  ChatMessage,
  Scenario,
  Scorecard,
  SessionResponse,
  SessionStatus,
} from "../types";

/** Local mirror of the backend countdown — falls back if /env not propagated. */
export const SESSION_MAX_SECONDS = 1500; // 25 min

type ChannelMessages = Record<Channel, ChatMessage[]>;
type ChannelTyping = Record<Channel, boolean>;

const emptyChannels = (): ChannelMessages => ({ pm: [], reviewer: [], teammate: [] });
const emptyTyping = (): ChannelTyping => ({ pm: false, reviewer: false, teammate: false });

interface SessionState {
  sessionId: string | null;
  status: SessionStatus | "idle";
  scenario: Scenario | null;
  startedAt: number | null; // ms epoch
  endedAt: number | null;

  channels: ChannelMessages;
  activeChannel: Channel;
  typing: ChannelTyping;

  workSurface: string;
  workSurfaceFilename: string;

  assistantTurns: AssistantTurn[];
  assistantPending: boolean;

  wsState: "closed" | "connecting" | "open";
  lastError: string | null;

  scorecard: Scorecard | null;
  scorecardLoading: boolean;
}

interface SessionActions {
  createSession: (role: string) => Promise<string>;
  loadSession: (sid: string) => Promise<void>;
  startSession: () => Promise<void>;
  connectWS: (sid: string) => void;
  disconnectWS: () => void;
  setActiveChannel: (channel: Channel) => void;
  sendMessage: (content: string) => void;
  setWorkSurface: (content: string) => void;
  flushArtifact: (trigger: "debounce" | "send" | "manual") => Promise<void>;
  sendAssistantQuery: (prompt: string) => Promise<void>;
  finishSession: () => Promise<void>;
  loadScorecard: () => Promise<void>;
  reset: () => void;
}

type Store = SessionState & SessionActions;

const initial: SessionState = {
  sessionId: null,
  status: "idle",
  scenario: null,
  startedAt: null,
  endedAt: null,
  channels: emptyChannels(),
  activeChannel: "pm",
  typing: emptyTyping(),
  workSurface: "",
  workSurfaceFilename: "main.py",
  assistantTurns: [],
  assistantPending: false,
  wsState: "closed",
  lastError: null,
  scorecard: null,
  scorecardLoading: false,
};

function fromSession(r: SessionResponse): Partial<SessionState> {
  const scenario =
    (r.scenario as Scenario | undefined) && Object.keys(r.scenario).length
      ? (r.scenario as Scenario)
      : null;
  return {
    sessionId: r.id,
    status: r.status,
    scenario,
    startedAt: r.started_at ? Date.parse(r.started_at) : null,
    endedAt: r.ended_at ? Date.parse(r.ended_at) : null,
    workSurface: scenario?.starter_artifact ?? "",
  };
}

// Module-scoped WS so it's not in the React tree (avoids stale closures).
let socket: WebSocket | null = null;

export const useStore = create<Store>((set, get) => ({
  ...initial,

  createSession: async (role) => {
    set({ lastError: null });
    const session = await api.createSession(role);
    set({ ...fromSession(session) });
    return session.id;
  },

  loadSession: async (sid) => {
    set({ lastError: null });
    const session = await api.getSession(sid);
    set({ ...fromSession(session) });
  },

  startSession: async () => {
    const { sessionId } = get();
    if (!sessionId) return;
    const session = await api.startSession(sessionId);
    set({ ...fromSession(session) });
  },

  connectWS: (sid) => {
    if (socket) {
      try {
        socket.close();
      } catch {
        /* ignore */
      }
    }
    set({ wsState: "connecting", lastError: null });

    socket = openSessionSocket(
      sid,
      (frame) => {
        if (frame.type === "ready") {
          // Hydrate channel histories from the event log replay.
          const channels = emptyChannels();
          (["pm", "reviewer", "teammate"] as Channel[]).forEach((ch) => {
            channels[ch] = frame.history[ch] ?? [];
          });
          set({ channels, wsState: "open" });
          return;
        }
        if (frame.type === "typing") {
          set((s) => ({ typing: { ...s.typing, [frame.channel]: frame.is_typing } }));
          return;
        }
        if (frame.type === "agent_message") {
          const msg: ChatMessage = {
            kind: "agent",
            channel: frame.channel,
            actor_name: frame.actor_name,
            content: frame.content,
            ts_ms: frame.ts_ms,
          };
          set((s) => ({
            channels: { ...s.channels, [frame.channel]: [...s.channels[frame.channel], msg] },
          }));
          return;
        }
        if (frame.type === "requirement_change") {
          const msg: ChatMessage = {
            kind: "requirement_change",
            channel: "pm",
            actor_name: frame.actor_name,
            content: frame.content,
            summary: frame.summary,
            ts_ms: frame.ts_ms,
          };
          set((s) => ({
            channels: { ...s.channels, pm: [...s.channels.pm, msg] },
            // Bring the candidate's attention to the PM channel.
            activeChannel: "pm",
          }));
          return;
        }
        if (frame.type === "error") {
          set({ lastError: frame.message });
          return;
        }
      },
      () => set({ wsState: "closed" }),
    );
  },

  disconnectWS: () => {
    if (socket) {
      try {
        socket.close();
      } catch {
        /* ignore */
      }
      socket = null;
    }
    set({ wsState: "closed" });
  },

  setActiveChannel: (channel) => set({ activeChannel: channel }),

  sendMessage: (content) => {
    const trimmed = content.trim();
    if (!trimmed || !socket) return;
    const { activeChannel } = get();
    const candidateMsg: ChatMessage = {
      kind: "candidate",
      channel: activeChannel,
      content: trimmed,
      ts_ms: get().startedAt ? Date.now() - (get().startedAt as number) : 0,
    };
    set((s) => ({
      channels: {
        ...s.channels,
        [activeChannel]: [...s.channels[activeChannel], candidateMsg],
      },
    }));
    sendCandidateMessage(socket, activeChannel, trimmed);
  },

  setWorkSurface: (content) => set({ workSurface: content }),

  flushArtifact: async (trigger) => {
    const { sessionId, workSurface, workSurfaceFilename } = get();
    if (!sessionId) return;
    try {
      await api.postArtifact(sessionId, workSurfaceFilename, workSurface, trigger);
    } catch (e) {
      // Snapshots are best-effort; surface as a soft error.
      set({ lastError: `snapshot failed: ${(e as Error).message}` });
    }
  },

  sendAssistantQuery: async (prompt) => {
    const { sessionId } = get();
    if (!sessionId) return;
    const queryTurn: AssistantTurn = { role: "user", content: prompt, ts_ms: Date.now() };
    set((s) => ({
      assistantTurns: [...s.assistantTurns, queryTurn],
      assistantPending: true,
    }));
    try {
      const r = await api.postAssistantQuery(sessionId, prompt);
      const responseTurn: AssistantTurn = {
        role: "assistant",
        content: r.response,
        ts_ms: r.response_ts_ms,
      };
      set((s) => ({ assistantTurns: [...s.assistantTurns, responseTurn] }));
    } catch (e) {
      set({ lastError: `assistant failed: ${(e as Error).message}` });
    } finally {
      set({ assistantPending: false });
    }
  },

  finishSession: async () => {
    const { sessionId } = get();
    if (!sessionId) return;
    // Flush a final 'send' snapshot before closing so the evaluator sees the
    // final state of the work surface.
    await get().flushArtifact("send");
    get().disconnectWS();
    const session = await api.endSession(sessionId);
    set({ ...fromSession(session) });
  },

  loadScorecard: async () => {
    const { sessionId } = get();
    if (!sessionId) return;
    set({ scorecardLoading: true, lastError: null });
    try {
      const sc = await api.getScorecard(sessionId);
      set({ scorecard: sc });
    } catch (e) {
      set({ lastError: `scorecard failed: ${(e as Error).message}` });
    } finally {
      set({ scorecardLoading: false });
    }
  },

  reset: () => {
    get().disconnectWS();
    set({ ...initial });
  },
}));
