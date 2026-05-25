/**
 * Top-bar countdown. Reads session-length + accessibility multiplier from the
 * store. Accents to warning under 60s, danger at zero.
 */
import { useEffect, useState } from "react";

import { maxSecondsFor, useStore } from "../state/store";

export default function Timer() {
  const startedAt = useStore((s) => s.startedAt);
  const sessionMinutes = useStore((s) => s.sessionMinutes);
  const accessibility = useStore((s) => s.accessibility);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (!startedAt) return;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [startedAt]);

  if (!startedAt) {
    return <span className="font-mono text-faint tabular-nums">--:--</span>;
  }
  const max = maxSecondsFor({ sessionMinutes, accessibility });
  const elapsed = Math.floor((now - startedAt) / 1000);
  const remaining = Math.max(0, max - elapsed);
  const m = Math.floor(remaining / 60);
  const s = remaining % 60;
  const tone =
    remaining === 0 ? "text-danger" : remaining < 60 ? "text-warning" : "text-fg";
  return (
    <span
      className={`font-mono tabular-nums ${tone}`}
      aria-label="time remaining"
      title={
        accessibility.extended_time_multiplier !== 1
          ? `Extended time ${accessibility.extended_time_multiplier}× active`
          : undefined
      }
    >
      {`${m}:${s.toString().padStart(2, "0")}`}
    </span>
  );
}
