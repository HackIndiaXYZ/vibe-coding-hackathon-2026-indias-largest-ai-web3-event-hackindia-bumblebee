/**
 * Top-bar countdown. Counts DOWN from SESSION_MAX_SECONDS, ticks once per second,
 * accents to warning color in the final minute. Always-visible per §7 spec.
 */
import { useEffect, useState } from "react";

import { SESSION_MAX_SECONDS } from "../state/store";

interface Props {
  startedAt: number | null;
}

export default function Timer({ startedAt }: Props) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!startedAt) return;
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, [startedAt]);

  if (!startedAt) {
    return <span className="font-mono text-faint tabular-nums">--:--</span>;
  }
  const elapsed = Math.floor((now - startedAt) / 1000);
  const remaining = Math.max(0, SESSION_MAX_SECONDS - elapsed);
  const m = Math.floor(remaining / 60);
  const s = remaining % 60;
  const tone =
    remaining === 0
      ? "text-danger"
      : remaining < 60
        ? "text-warning"
        : "text-fg";
  return (
    <span className={`font-mono tabular-nums ${tone}`} aria-label="time remaining">
      {`${m}:${s.toString().padStart(2, "0")}`}
    </span>
  );
}
