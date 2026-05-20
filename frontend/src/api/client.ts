/**
 * REST client. Requests are routed through Vite's /api proxy to the FastAPI
 * backend in dev. In production these would be absolute URLs.
 */
import type { Scorecard, SessionResponse } from "../types";

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
  return (await r.json()) as T;
}

export const api = {
  createSession: (role: string) =>
    request<SessionResponse>("/sessions", {
      method: "POST",
      body: JSON.stringify({ role }),
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
      {
        method: "POST",
        body: JSON.stringify({ prompt }),
      },
    ),

  getScorecard: (id: string) =>
    request<Scorecard>(`/sessions/${id}/scorecard`),
};
