/**
 * WebSocket client for the session orchestrator. Vite's /ws proxy targets the
 * backend WS endpoint, so we connect to /ws/sessions/{id}/ws on the dev port.
 */
import type { CandidateMessageFrame, ServerFrame } from "../types";

export type FrameHandler = (frame: ServerFrame) => void;

export function openSessionSocket(
  sessionId: string,
  onFrame: FrameHandler,
  onClose?: (ev: CloseEvent) => void,
): WebSocket {
  // Vite proxies /ws → ws://localhost:8000 (see vite.config.ts).
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  const url = `${proto}//${window.location.host}/ws/sessions/${sessionId}/ws`;
  const ws = new WebSocket(url);

  ws.addEventListener("message", (ev) => {
    try {
      const frame = JSON.parse(ev.data) as ServerFrame;
      onFrame(frame);
    } catch (err) {
      console.error("ws frame parse failed", err, ev.data);
    }
  });

  if (onClose) ws.addEventListener("close", onClose);

  return ws;
}

export function sendCandidateMessage(
  ws: WebSocket,
  channel: "pm" | "reviewer" | "teammate",
  content: string,
) {
  const frame: CandidateMessageFrame = {
    type: "candidate_message",
    channel,
    content,
  };
  ws.send(JSON.stringify(frame));
}
