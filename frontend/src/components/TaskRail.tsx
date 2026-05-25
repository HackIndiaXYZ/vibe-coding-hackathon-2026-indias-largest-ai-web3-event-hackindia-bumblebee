/**
 * Format B left rail: task list + per-task description, click to switch
 * editor buffer.
 */
import { useStore } from "../state/store";
import type { ScenarioB } from "../types";

export default function TaskRail() {
  const scenario = useStore((s) => s.scenario) as ScenarioB | null;
  const activeTaskId = useStore((s) => s.activeTaskId);
  const setActiveTask = useStore((s) => s.setActiveTask);

  if (!scenario || "cast" in scenario) {
    return <p className="p-4 text-xs text-faint">No task set loaded.</p>;
  }

  return (
    <nav aria-label="Coding tasks" className="flex flex-col h-full">
      <p className="text-xs uppercase tracking-wider text-faint px-3 pt-3 pb-2">
        Coding tasks
      </p>
      <ul className="flex flex-col flex-1 overflow-y-auto">
        {scenario.tasks.map((t, i) => {
          const active = t.id === activeTaskId;
          return (
            <li key={t.id}>
              <button
                type="button"
                onClick={() => setActiveTask(t.id)}
                className={`w-full text-left px-3 py-3 border-l-2 transition-colors ${
                  active
                    ? "bg-surface-2 border-accent"
                    : "border-transparent hover:bg-surface-2/60"
                }`}
              >
                <div className="flex items-baseline justify-between gap-2 mb-1">
                  <p className="text-sm text-fg">
                    <span className="text-faint mr-1.5">{i + 1}.</span>
                    {t.title}
                  </p>
                  <span className="text-[10px] text-faint">~{t.expected_minutes}m</span>
                </div>
                <p className="text-xs text-muted leading-relaxed line-clamp-3">
                  {t.description}
                </p>
              </button>
              {active && (
                <details className="px-3 pb-3 text-xs">
                  <summary className="cursor-pointer text-faint hover:text-muted py-1">
                    Visible tests
                  </summary>
                  <pre className="mt-1 p-2 bg-bg/60 border border-border rounded text-[11px] text-fg overflow-x-auto font-mono">
                    {t.visible_tests}
                  </pre>
                </details>
              )}
            </li>
          );
        })}
      </ul>
      <div className="border-t border-border p-3 text-[11px] text-faint leading-relaxed">
        Hidden tests run on submit. No AI assistant available in this format.
      </div>
    </nav>
  );
}
