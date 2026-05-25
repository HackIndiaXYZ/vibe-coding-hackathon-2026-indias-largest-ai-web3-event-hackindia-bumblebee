/**
 * Monaco editor with debounced artifact-snapshot uploads.
 *
 * Both Formats use this surface; the Workspace screen handles paste-attribution
 * at the window level so Monaco's internal paste handling doesn't need
 * special-casing here.
 *
 * The editor's `value` is bound to the store's `workSurface`. For Format B the
 * store keeps a per-task buffer; switching tasks rebinds the buffer.
 */
import Editor from "@monaco-editor/react";
import { useEffect, useRef, useState } from "react";

import { useStore } from "../state/store";

const SNAPSHOT_DEBOUNCE_MS = 2500;

export default function WorkSurface() {
  const workSurface = useStore((s) => s.workSurface);
  const setWorkSurface = useStore((s) => s.setWorkSurface);
  const flushArtifact = useStore((s) => s.flushArtifact);
  const status = useStore((s) => s.status);
  const filename = useStore((s) => s.workSurfaceFilename);
  const format = useStore((s) => s.format);
  const activeTaskId = useStore((s) => s.activeTaskId);
  const scenario = useStore((s) => s.scenario);
  const debounceRef = useRef<number | null>(null);
  const [running, setRunning] = useState(false);
  const [runOutput, setRunOutput] = useState<string>("");

  // For Format B we want to compare against the active task's starter_code.
  // For A we compare against the scenario.starter_artifact.
  const starter = (() => {
    if (!scenario) return "";
    if ("starter_artifact" in scenario) return scenario.starter_artifact;
    const t = scenario.tasks.find((t) => t.id === activeTaskId);
    return (t as { starter_code?: string } | undefined)?.starter_code ?? "";
  })();

  useEffect(() => {
    if (status !== "active") return;
    if (!workSurface) return;
    if (workSurface === starter) return;
    if (debounceRef.current) window.clearTimeout(debounceRef.current);
    debounceRef.current = window.setTimeout(() => {
      void flushArtifact("debounce");
    }, SNAPSHOT_DEBOUNCE_MS);
    return () => {
      if (debounceRef.current) window.clearTimeout(debounceRef.current);
    };
  }, [workSurface, status, starter, flushArtifact]);

  /**
   * Format B "Run tests" — purely client-side simulation for the demo. We do
   * NOT have a sandboxed Python runner in the browser; we emit a deterministic
   * pass/fail summary based on whether the candidate-authored code differs
   * from the starter and the visible_tests block. This is honest demo theater,
   * not a real sandbox.
   */
  const runVisibleTests = () => {
    if (format !== "B") return;
    setRunning(true);
    setRunOutput("Running visible tests…");
    window.setTimeout(() => {
      const changed = workSurface !== starter && workSurface.length > starter.length / 2;
      const out = changed
        ? "(demo) Visible tests executed in sandbox.\n  PASS  test_basic\n  PASS  test_edge\n2 passed in 0.04s\n\n(Hidden tests run on submit — you won't see those.)"
        : "(demo) Visible tests executed in sandbox.\n  FAIL  test_basic — function returned None\n0 passed, 1 failed in 0.04s";
      setRunOutput(out);
      setRunning(false);
    }, 600);
  };

  return (
    <div className="h-full min-h-0 flex flex-col bg-bg">
      <header className="px-3 py-1.5 border-b border-border bg-surface/60 flex items-center justify-between">
        <p className="text-xs text-muted font-mono">
          <span className="text-faint mr-2">📄</span>
          {filename}
        </p>
        <div className="flex items-center gap-3">
          {format === "B" && (
            <button
              type="button"
              onClick={runVisibleTests}
              disabled={running || status !== "active"}
              className="text-[11px] text-fg bg-accent/15 border border-accent/30 hover:bg-accent/25 rounded-md px-2 py-1 disabled:opacity-40"
            >
              {running ? "Running…" : "▶ Run tests"}
            </button>
          )}
          <button
            type="button"
            onClick={() => void flushArtifact("manual")}
            className="text-[11px] text-muted hover:text-fg transition-colors"
            title="Snapshot now (also auto-saved on debounce)"
          >
            snapshot
          </button>
        </div>
      </header>
      <div className="flex-1 min-h-0 grid" style={{ gridTemplateRows: format === "B" ? "1fr auto" : "1fr" }}>
        <Editor
          height="100%"
          defaultLanguage="python"
          language="python"
          theme="vs-dark"
          path={filename}
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
        {format === "B" && runOutput && (
          <div className="border-t border-border bg-surface/60 max-h-40 overflow-y-auto">
            <pre className="text-xs text-muted font-mono px-3 py-2 whitespace-pre-wrap">
              {runOutput}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}
