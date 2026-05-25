/** Shared TypeScript types — v3.0. Must mirror backend Pydantic models. */

export type Channel = "pm" | "reviewer" | "peer";
export const CHANNELS: readonly Channel[] = ["pm", "reviewer", "peer"] as const;

export type SessionFormat = "A" | "B";
export type IntegrityTier = "standard" | "enhanced";

export type SessionStatus =
  | "created"
  | "briefing"
  | "active"
  | "wrapping"
  | "scoring"
  | "complete";

export interface AccessibilityPrefs {
  mode_enabled: boolean;
  extended_time_multiplier: number; // 1.0, 1.5, or 2.0
  reduced_motion: boolean;
  high_contrast: boolean;
  dyslexia_font: boolean;
  screen_reader_optimized: boolean;
}

export const DEFAULT_ACCESSIBILITY: AccessibilityPrefs = {
  mode_enabled: false,
  extended_time_multiplier: 1.0,
  reduced_motion: false,
  high_contrast: false,
  dyslexia_font: false,
  screen_reader_optimized: false,
};

// ---- Format A scenario shape (mirrors backend Scenario) ----

export interface Persona {
  name: string;
  role: string;
  style: string;
  hidden_agenda: string;
}

export interface Cast {
  pm: Persona;
  reviewer: Persona;
  peer: Persona;
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

export interface ScenarioA {
  company_name: string;
  company_context: string;
  role: string;
  candidate_role_summary: string;
  cast: Cast;
  tasks: Task[];
  starter_artifact: string;
  twist: Twist;
}

// ---- Format B task-set shape (mirrors backend TaskSet) ----

export interface CodingTask {
  id: string;
  title: string;
  description: string;
  starter_code: string;
  visible_tests: string;
  hidden_tests_description: string;
  expected_minutes: number;
}

export interface ScenarioB {
  company_name: string;
  company_context: string;
  role: string;
  candidate_role_summary: string;
  tasks: CodingTask[];
  evaluator_notes: string;
}

export type AnyScenario = ScenarioA | ScenarioB;

export function isFormatA(s: AnyScenario | null | undefined): s is ScenarioA {
  return !!s && "cast" in s && "twist" in s;
}

// ---- Session ----

export interface SessionResponse {
  id: string;
  role: string;
  format: SessionFormat;
  integrity_tier: IntegrityTier;
  is_practice: boolean;
  session_minutes: number;
  status: SessionStatus;
  scenario: AnyScenario | Record<string, never>;
  accessibility: AccessibilityPrefs;
  candidate_label: string | null;
  created_at: string;
  started_at: string | null;
  ended_at: string | null;
}

// ---- Chat messages (Format A only) ----

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

// ---- v3 Scorecard ----

export interface ScorecardEvidence {
  event_id: number;
  ts_ms: number;
  quote: string;
  reasoning: string;
}

export type QualitativeBand =
  | "Strong"
  | "Solid"
  | "Mixed"
  | "Limited"
  | "Insufficient signal";

export type EvaluatorAgreement = "high" | "medium" | "low" | "divergent";

export interface ScorecardAxis {
  axis: string;
  score_0_10: number;
  confidence_pm: number;
  band: QualitativeBand;
  agreement: EvaluatorAgreement;
  summary: string;
  evidence: ScorecardEvidence[];
  flagged: boolean;
}

export interface IntegrityContext {
  tab_focus_lost_count: number;
  tab_focus_total_away_ms: number;
  paste_event_count: number;
  paste_external_bytes: number;
  ai_assistant_turn_count: number;
  cast_message_count: number;
  notes: string[];
}

export interface Scorecard {
  session_id: string;
  format: SessionFormat;
  is_practice: boolean;
  disclaimer: string;
  axes: ScorecardAxis[];
  integrity: IntegrityContext;
}

// ---- Right-to-explanation ----

export interface AxisExplanation {
  axis: string;
  plain_language: string;
  what_we_measure: string;
  what_we_dont_measure: string;
}

export interface Explanation {
  session_id: string;
  format: SessionFormat;
  intro: string;
  per_axis: AxisExplanation[];
  rights: string[];
  sub_processors: string[];
}

// ---- Appeal ----

export interface AppealResponse {
  id: number;
  session_id: string;
  status: string;
  created_at: string;
}

// ---- Recruiter dashboard ----

export interface RecruiterSessionRow {
  id: string;
  role: string;
  format: SessionFormat;
  status: SessionStatus;
  candidate_label: string | null;
  is_practice: boolean;
  started_at: string | null;
  ended_at: string | null;
  axes_summary: {
    axis: string;
    score_0_10: number;
    band: QualitativeBand;
    flagged: boolean;
  }[];
}

// ---- WebSocket protocol ----

export type ServerFrame =
  | { type: "ready"; history: Record<Channel, ChatMessage[]> }
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

export interface CandidateMessageFrame {
  type: "candidate_message";
  channel: Channel;
  content: string;
}
