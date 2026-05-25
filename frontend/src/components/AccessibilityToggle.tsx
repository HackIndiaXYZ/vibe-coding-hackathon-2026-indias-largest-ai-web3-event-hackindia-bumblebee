/**
 * Compact dropdown for the v3 Accessibility Mode (§5.2).
 *
 * Self-elected, no documentation required, never surfaces to the recruiter.
 * Persists to the Zustand store (and through it, to the <html> element).
 */
import { useEffect, useRef, useState } from "react";

import { useStore } from "../state/store";

export default function AccessibilityToggle() {
  const a11y = useStore((s) => s.accessibility);
  const update = useStore((s) => s.updateAccessibility);
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [open]);

  const summary = a11y.mode_enabled
    ? `Accessibility · on${a11y.extended_time_multiplier !== 1 ? ` · ${a11y.extended_time_multiplier}× time` : ""}`
    : "Accessibility";

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="dialog"
        aria-expanded={open}
        className={`text-xs px-2.5 py-1 rounded-md border ${
          a11y.mode_enabled
            ? "border-accent text-accent bg-accent-soft/40"
            : "border-border text-muted hover:text-fg hover:border-border-strong"
        } transition-colors`}
      >
        ♿ {summary}
      </button>
      {open && (
        <div
          role="dialog"
          aria-label="Accessibility preferences"
          className="absolute right-0 top-full mt-2 z-50 w-80 rounded-lg border border-border bg-surface p-4 shadow-xl"
        >
          <p className="text-xs uppercase tracking-wider text-faint mb-2">
            Accessibility Mode
          </p>
          <p className="text-xs text-muted leading-relaxed mb-3">
            Self-elected. Never surfaces to the recruiter. Time accommodation does
            not affect your scorecard. WCAG 2.2 Level AA.
          </p>
          <label className="flex items-center gap-2 mb-3">
            <input
              type="checkbox"
              checked={a11y.mode_enabled}
              onChange={(e) => update({ mode_enabled: e.target.checked })}
              className="accent-accent"
            />
            <span className="text-sm text-fg">Enable Accessibility Mode</span>
          </label>

          <div className="space-y-2 text-sm">
            <div>
              <p className="text-xs text-faint mb-1">Extended time</p>
              <div className="flex gap-1">
                {[1.0, 1.5, 2.0].map((m) => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => update({ extended_time_multiplier: m, mode_enabled: m !== 1 || a11y.mode_enabled })}
                    className={`flex-1 text-xs py-1 rounded-md border ${
                      a11y.extended_time_multiplier === m
                        ? "border-accent text-accent bg-accent-soft/40"
                        : "border-border text-muted hover:text-fg"
                    }`}
                  >
                    {m}×
                  </button>
                ))}
              </div>
            </div>

            <Toggle
              label="High contrast"
              checked={a11y.high_contrast}
              onChange={(v) => update({ high_contrast: v })}
            />
            <Toggle
              label="Reduced motion"
              checked={a11y.reduced_motion}
              onChange={(v) => update({ reduced_motion: v })}
            />
            <Toggle
              label="Dyslexia-friendly font"
              checked={a11y.dyslexia_font}
              onChange={(v) => update({ dyslexia_font: v })}
            />
            <Toggle
              label="Screen-reader optimizations"
              checked={a11y.screen_reader_optimized}
              onChange={(v) => update({ screen_reader_optimized: v })}
            />
          </div>
        </div>
      )}
    </div>
  );
}

function Toggle({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="flex items-center justify-between cursor-pointer">
      <span className="text-fg">{label}</span>
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="accent-accent"
      />
    </label>
  );
}
