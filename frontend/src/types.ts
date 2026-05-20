/** Shared TypeScript types — must mirror backend Pydantic models. */

export type Channel = "pm" | "reviewer" | "teammate";
export const CHANNELS: readonly Channel[] = ["pm", "reviewer", "teammate"] as const;

export type SessionStatus =
  | "created"
  | "briefing"
  | "active"
  | "wrapping"
  | "scoring"
  | "complete";

export interface Persona {
  name: string;
  role: string;
  style: string;
  hidden_agenda: string;
}

export interface Cast {
  pm: Persona;
  reviewer: Persona;
  teammate: Persona;
}

export interface Task {
  id: string;
  title: string;
  description: string;
}

export interface Twist {
  trigger_after_turn: number;
  pm_message: string;
  summary: string;
}

export interface Scenario {
  company_name: string;
  company_context: string;
  role: string;
  candidate_role_summary: string;
  cast: Cast;
  tasks: Task[];
  starter_artifact: string;
  twist: Twist;
}

export interface SessionResponse {
  id: string;
  role: string;
  status: SessionStatus;
  scenario: Scenario | Record<string, never>;
  created_at: string;
  started_at: string | null;
  ended_at: string | null;
}

/** A single rendered message in a chat channel. */
export interface ChatMessage {
  kind: "candidate" | "agent" | "requirement_change";
  channel: Channel;
  actor_name?: string;
  content: string;
  summary?: string;
  ts_ms: number;
}

export interface AssistantTurn {
  role: "user" | "assistant";
  content: string;
  ts_ms: number;
}

/** Scorecard payload. */
export interface ScorecardEvidence {
  event_id: number;
  ts_ms: number;
  quote: string;
  reasoning: string;
}

export interface ScorecardAxis {
  axis: string;
  score: number; // 1-5
  summary: string;
  evidence: ScorecardEvidence[];
  flagged: boolean;
}

export interface Scorecard {
  session_id: string;
  disclaimer: string;
  axes: ScorecardAxis[];
}

/** Server → client WebSocket frames. */
export type ServerFrame =
  | {
      type: "ready";
      history: Record<Channel, ChatMessage[]>;
    }
  | { type: "typing"; channel: Channel; is_typing: boolean }
  | {
      type: "agent_message";
      channel: Channel;
      actor_name: string;
      content: string;
      ts_ms: number;
    }
  | {
      type: "requirement_change";
      channel: "pm";
      actor_name: string;
      content: string;
      summary: string;
      ts_ms: number;
    }
  | { type: "error"; message: string };

/** Client → server WebSocket frames. */
export interface CandidateMessageFrame {
  type: "candidate_message";
  channel: Channel;
  content: string;
}
