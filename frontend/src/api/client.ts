/**
 * REST client — v3.0.
 *
 * Routes through Vite's /api proxy to the FastAPI backend in dev. In
 * production these would be absolute URLs.
 */
import type {
  AccessibilityPrefs,
  AppealResponse,
  Explanation,
  IntegrityTier,
  RecruiterSessionRow,
  Scorecard,
  SessionFormat,
  SessionResponse,
} from "../types";

const BASE = "/api";

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init.headers },
    ...init,
  });
  if (!r.ok) {
    let detail = `${r.status} ${r.statusText}`;
    try {
      const body = await r.json();
      if (body?.detail) detail = `${detail} — ${body.detail}`;
    } catch {
      /* ignore parse error */
    }
    throw new Error(detail);
  }
  // Some endpoints (204/empty) need a guard, but everything here returns JSON.
  return (await r.json()) as T;
}

export interface CreateSessionPayload {
  role: string;
  format: SessionFormat;
  session_minutes?: number;
  integrity_tier?: IntegrityTier;
  accessibility?: AccessibilityPrefs;
  is_practice?: boolean;
  candidate_label?: string | null;
}

export const api = {
  createSession: (payload: CreateSessionPayload) =>
    request<SessionResponse>("/sessions", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getSession: (id: string) => request<SessionResponse>(`/sessions/${id}`),

  startSession: (id: string) =>
    request<SessionResponse>(`/sessions/${id}/start`, { method: "POST" }),

  endSession: (id: string) =>
    request<SessionResponse>(`/sessions/${id}/end`, { method: "POST" }),

  postArtifact: (
    id: string,
    filename: string,
    content: string,
    trigger: "debounce" | "send" | "manual" = "debounce",
  ) =>
    request<{ ts_ms: number; filename: string; bytes: number }>(
      `/sessions/${id}/artifact`,
      {
        method: "POST",
        body: JSON.stringify({ filename, content, trigger }),
      },
    ),

  postAssistantQuery: (id: string, prompt: string) =>
    request<{ response: string; query_ts_ms: number; response_ts_ms: number }>(
      `/sessions/${id}/assistant`,
      { method: "POST", body: JSON.stringify({ prompt }) },
    ),

  postTabFocus: (id: string, kind: "lost" | "regained", awayMs?: number) =>
    request<{ ts_ms: number }>(`/sessions/${id}/integrity/tab-focus`, {
      method: "POST",
      body: JSON.stringify({ kind, away_ms: awayMs ?? null }),
    }),

  postPaste: (
    id: string,
    target: "work_surface" | "chat" | "assistant",
    bytes: number,
    source: "external" | "internal" | "unknown",
    preview: string,
  ) =>
    request<{ ts_ms: number }>(`/sessions/${id}/integrity/paste`, {
      method: "POST",
      body: JSON.stringify({ target, bytes, source, preview }),
    }),

  getScorecard: (id: string) => request<Scorecard>(`/sessions/${id}/scorecard`),

  getExplanation: (id: string) =>
    request<Explanation>(`/sessions/${id}/explanation`),

  postAppeal: (id: string, reason: string) =>
    request<AppealResponse>(`/sessions/${id}/appeal`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),

  listRecruiterSessions: () =>
    request<RecruiterSessionRow[]>("/recruiter/sessions"),
};
