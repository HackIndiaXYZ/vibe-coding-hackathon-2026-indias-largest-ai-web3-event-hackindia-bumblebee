/**
 * Global session + UI store — v3.0.
 *
 * v3 changes:
 *   - Format-aware (A vs B).
 *   - Per-task work-surface buffers for Format B.
 *   - Accessibility prefs persisted in-store + applied to <html>.
 *   - Integrity event capture (tab focus + paste attribution) — descriptive,
 *     never scored; surfaces in the recruiter view and the scorecard
 *     Integrity Context section.
 */
import { create } from "zustand";

import { api, type CreateSessionPayload } from "../api/client";
import { openSessionSocket, sendCandidateMessage } from "../api/ws";
import type {
  AccessibilityPrefs,
  AnyScenario,
  AssistantTurn,
  Channel,
  ChatMessage,
  IntegrityTier,
  Scorecard,
  ScenarioA,
  ScenarioB,
  SessionFormat,
  SessionResponse,
  SessionStatus,
} from "../types";
import { DEFAULT_ACCESSIBILITY, isFormatA } from "../types";

type ChannelMessages = Record<Channel, ChatMessage[]>;
type ChannelTyping = Record<Channel, boolean>;

const emptyChannels = (): ChannelMessages => ({ pm: [], reviewer: [], peer: [] });
const emptyTyping = (): ChannelTyping => ({ pm: false, reviewer: false, peer: false });

interface SessionState {
  sessionId: string | null;
  status: SessionStatus | "idle";
  format: SessionFormat;
  isPractice: boolean;
  integrityTier: IntegrityTier;
  sessionMinutes: number;
  scenario: AnyScenario | null;
  startedAt: number | null; // ms epoch
  endedAt: number | null;

  // Format A surfaces
  channels: ChannelMessages;
  activeChannel: Channel;
  typing: ChannelTyping;
  assistantTurns: AssistantTurn[];
  assistantPending: boolean;

  // Work surface — A uses a single buffer; B keys by task id.
  workSurface: string;
  workSurfaceFilename: string;
  taskBuffers: Record<string, string>; // Format B: task_id → code
  activeTaskId: string | null; // Format B

  wsState: "closed" | "connecting" | "open";
  lastError: string | null;

  accessibility: AccessibilityPrefs;

  scorecard: Scorecard | null;
  scorecardLoading: boolean;
}

interface SessionActions {
  createSession: (payload: CreateSessionPayload) => Promise<string>;
  loadSession: (sid: string) => Promise<void>;
  startSession: () => Promise<void>;
  connectWS: (sid: string) => void;
  disconnectWS: () => void;
  setActiveChannel: (channel: Channel) => void;
  sendMessage: (content: string) => void;
  setWorkSurface: (content: string) => void;
  setActiveTask: (taskId: string) => void;
  setTaskBuffer: (taskId: string, content: string) => void;
  flushArtifact: (trigger: "debounce" | "send" | "manual") => Promise<void>;
  sendAssistantQuery: (prompt: string) => Promise<void>;
  finishSession: () => Promise<void>;
  loadScorecard: () => Promise<void>;
  logTabFocus: (kind: "lost" | "regained", awayMs?: number) => Promise<void>;
  logPaste: (
    target: "work_surface" | "chat" | "assistant",
    bytes: number,
    source: "external" | "internal" | "unknown",
    preview: string,
  ) => Promise<void>;
  updateAccessibility: (patch: Partial<AccessibilityPrefs>) => void;
  reset: () => void;
}

type Store = SessionState & SessionActions;

const initial: SessionState = {
  sessionId: null,
  status: "idle",
  format: "A",
  isPractice: false,
  integrityTier: "standard",
  sessionMinutes: 60,
  scenario: null,
  startedAt: null,
  endedAt: null,
  channels: emptyChannels(),
  activeChannel: "pm",
  typing: emptyTyping(),
  workSurface: "",
  workSurfaceFilename: "main.py",
  taskBuffers: {},
  activeTaskId: null,
  assistantTurns: [],
  assistantPending: false,
  wsState: "closed",
  lastError: null,
  accessibility: { ...DEFAULT_ACCESSIBILITY },
  scorecard: null,
  scorecardLoading: false,
};

function sessionMaxSeconds(session: Pick<SessionState, "sessionMinutes" | "accessibility">): number {
  return Math.round(
    session.sessionMinutes * 60 * (session.accessibility.extended_time_multiplier ?? 1.0),
  );
}

function fromSession(r: SessionResponse): Partial<SessionState> {
  const raw =
    (r.scenario as AnyScenario | undefined) && Object.keys(r.scenario).length
      ? (r.scenario as AnyScenario)
      : null;
  const scenario: AnyScenario | null = raw;
  let workSurface = "";
  let taskBuffers: Record<string, string> = {};
  let activeTaskId: string | null = null;
  let workSurfaceFilename = "main.py";

  if (scenario) {
    if (isFormatA(scenario)) {
      workSurface = (scenario as ScenarioA).starter_artifact ?? "";
    } else {
      const sb = scenario as ScenarioB;
      taskBuffers = Object.fromEntries(sb.tasks.map((t) => [t.id, t.starter_code]));
      activeTaskId = sb.tasks[0]?.id ?? null;
      workSurface = activeTaskId ? taskBuffers[activeTaskId] : "";
      workSurfaceFilename = activeTaskId ? `${activeTaskId}.py` : "main.py";
    }
  }
  return {
    sessionId: r.id,
    status: r.status,
    format: r.format,
    isPractice: r.is_practice,
    integrityTier: r.integrity_tier,
    sessionMinutes: r.session_minutes,
    scenario,
    accessibility: { ...DEFAULT_ACCESSIBILITY, ...r.accessibility },
    startedAt: r.started_at ? Date.parse(r.started_at) : null,
    endedAt: r.ended_at ? Date.parse(r.ended_at) : null,
    workSurface,
    workSurfaceFilename,
    taskBuffers,
    activeTaskId,
  };
}

// Module-scoped WS so it's not in the React tree (avoids stale closures).
let socket: WebSocket | null = null;

export const useStore = create<Store>((set, get) => ({
  ...initial,

  createSession: async (payload) => {
    set({ lastError: null });
    const r = await api.createSession(payload);
    set({ ...fromSession(r) });
    return r.id;
  },

  loadSession: async (sid) => {
    set({ lastError: null });
    const r = await api.getSession(sid);
    set({ ...fromSession(r) });
  },

  startSession: async () => {
    const { sessionId } = get();
    if (!sessionId) return;
    const r = await api.startSession(sessionId);
    set({ ...fromSession(r) });
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
          const channels = emptyChannels();
          (["pm", "reviewer", "peer"] as Channel[]).forEach((ch) => {
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
    const { activeChannel, startedAt } = get();
    const candidateMsg: ChatMessage = {
      kind: "candidate",
      channel: activeChannel,
      content: trimmed,
      ts_ms: startedAt ? Date.now() - startedAt : 0,
    };
    set((s) => ({
      channels: {
        ...s.channels,
        [activeChannel]: [...s.channels[activeChannel], candidateMsg],
      },
    }));
    sendCandidateMessage(socket, activeChannel, trimmed);
  },

  setWorkSurface: (content) => {
    const { activeTaskId, format } = get();
    set({ workSurface: content });
    if (format === "B" && activeTaskId) {
      set((s) => ({ taskBuffers: { ...s.taskBuffers, [activeTaskId]: content } }));
    }
  },

  setActiveTask: (taskId) => {
    const { taskBuffers, format } = get();
    if (format !== "B") return;
    const next = taskBuffers[taskId] ?? "";
    set({
      activeTaskId: taskId,
      workSurface: next,
      workSurfaceFilename: `${taskId}.py`,
    });
  },

  setTaskBuffer: (taskId, content) =>
    set((s) => ({ taskBuffers: { ...s.taskBuffers, [taskId]: content } })),

  flushArtifact: async (trigger) => {
    const { sessionId, workSurface, workSurfaceFilename } = get();
    if (!sessionId) return;
    try {
      await api.postArtifact(sessionId, workSurfaceFilename, workSurface, trigger);
    } catch (e) {
      set({ lastError: `snapshot failed: ${(e as Error).message}` });
    }
  },

  sendAssistantQuery: async (prompt) => {
    const { sessionId, format } = get();
    if (!sessionId) return;
    if (format !== "A") {
      set({ lastError: "AI assistant is disabled in Format B." });
      return;
    }
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
    await get().flushArtifact("send");
    get().disconnectWS();
    const r = await api.endSession(sessionId);
    set({ ...fromSession(r) });
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

  logTabFocus: async (kind, awayMs) => {
    const { sessionId, status } = get();
    if (!sessionId || status !== "active") return;
    try {
      await api.postTabFocus(sessionId, kind, awayMs);
    } catch {
      /* best-effort — never block the candidate on telemetry */
    }
  },

  logPaste: async (target, bytes, source, preview) => {
    const { sessionId, status } = get();
    if (!sessionId || status !== "active") return;
    try {
      await api.postPaste(sessionId, target, bytes, source, preview);
    } catch {
      /* best-effort */
    }
  },

  updateAccessibility: (patch) => {
    set((s) => ({ accessibility: { ...s.accessibility, ...patch } }));
    applyAccessibilityToDocument(get().accessibility);
  },

  reset: () => {
    get().disconnectWS();
    set({ ...initial });
    applyAccessibilityToDocument(DEFAULT_ACCESSIBILITY);
  },
}));

// ---- side-effects: apply accessibility prefs to <html> ----

export function applyAccessibilityToDocument(prefs: AccessibilityPrefs) {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  root.classList.toggle("a11y-reduced-motion", prefs.reduced_motion);
  root.classList.toggle("a11y-high-contrast", prefs.high_contrast);
  root.classList.toggle("a11y-dyslexia", prefs.dyslexia_font);
  root.dataset.a11yMode = prefs.mode_enabled ? "on" : "off";
}

// ---- derived: session timer ----

export function maxSecondsFor(s: Pick<SessionState, "sessionMinutes" | "accessibility">) {
  return sessionMaxSeconds(s);
}
