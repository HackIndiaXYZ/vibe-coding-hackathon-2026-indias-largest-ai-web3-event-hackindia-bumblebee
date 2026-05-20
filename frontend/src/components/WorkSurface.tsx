/**
 * Monaco editor with debounced artifact-snapshot uploads.
 *
 * - The editor's `value` is bound to the store's `workSurface`.
 * - Every change triggers a 2.5s debounce; when it settles, we POST a
 *   `debounce`-triggered artifact_snapshot. This is what Phase 4 evaluators
 *   read to see how the candidate's code evolved.
 */
import Editor from "@monaco-editor/react";
import { useEffect, useRef } from "react";

import { useStore } from "../state/store";

const SNAPSHOT_DEBOUNCE_MS = 2500;

export default function WorkSurface() {
  const workSurface = useStore((s) => s.workSurface);
  const setWorkSurface = useStore((s) => s.setWorkSurface);
  const flushArtifact = useStore((s) => s.flushArtifact);
  const status = useStore((s) => s.status);
  const debounceRef = useRef<number | null>(null);
  const firstRenderRef = useRef(true);

  // Debounced snapshot on every change.
  useEffect(() => {
    if (firstRenderRef.current) {
      firstRenderRef.current = false;
      return;
    }
    if (status !== "active") return;
    if (debounceRef.current) {
      window.clearTimeout(debounceRef.current);
    }
    debounceRef.current = window.setTimeout(() => {
      void flushArtifact("debounce");
    }, SNAPSHOT_DEBOUNCE_MS);
    return () => {
      if (debounceRef.current) window.clearTimeout(debounceRef.current);
    };
  }, [workSurface, status, flushArtifact]);

  return (
    <div className="h-full min-h-0 flex flex-col bg-bg">
      <header className="px-3 py-1.5 border-b border-border bg-surface/60 flex items-center justify-between">
        <p className="text-xs text-muted font-mono">
          <span className="text-faint mr-2">📄</span>main.py
        </p>
        <button
          type="button"
          onClick={() => void flushArtifact("manual")}
          className="text-[11px] text-muted hover:text-fg transition-colors"
          title="Snapshot now (also auto-saved on debounce)"
        >
          snapshot
        </button>
      </header>
      <div className="flex-1 min-h-0">
        <Editor
          height="100%"
          defaultLanguage="python"
          theme="vs-dark"
          value={workSurface}
          onChange={(v) => setWorkSurface(v ?? "")}
          options={{
            fontSize: 13,
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            wordWrap: "on",
            tabSize: 4,
            fontFamily: "JetBrains Mono, Fira Code, monospace",
            renderWhitespace: "selection",
            automaticLayout: true,
          }}
        />
      </div>
    </div>
  );
}
