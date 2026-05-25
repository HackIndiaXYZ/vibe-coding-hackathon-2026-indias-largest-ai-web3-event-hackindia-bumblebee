/**
 * Score + confidence-interval display for one rubric axis.
 *
 * Renders a 0–10 axis with the point estimate marked and the ± interval
 * shaded behind it. Tone is band-driven (Strong=green, Solid=blue, etc.).
 */
import type { QualitativeBand } from "../types";

interface Props {
  score: number;
  pm: number;
  band: QualitativeBand;
}

const BAND_BG: Record<QualitativeBand, string> = {
  Strong: "bg-band-strong",
  Solid: "bg-band-solid",
  Mixed: "bg-band-mixed",
  Limited: "bg-band-limited",
  "Insufficient signal": "bg-band-insufficient",
};

export default function ConfidenceBar({ score, pm, band }: Props) {
  const lo = Math.max(0, score - pm);
  const hi = Math.min(10, score + pm);
  const tone = BAND_BG[band] ?? "bg-band-mixed";
  return (
    <div className="w-full">
      <div className="relative h-2 rounded-full bg-surface-3 overflow-hidden">
        <div
          className={`absolute top-0 h-full ${tone} opacity-40`}
          style={{ left: `${lo * 10}%`, width: `${(hi - lo) * 10}%` }}
          aria-hidden
        />
        <div
          className={`absolute top-0 h-full w-[2px] ${tone}`}
          style={{ left: `calc(${score * 10}% - 1px)` }}
          aria-hidden
        />
      </div>
      <div className="flex items-center justify-between mt-1 text-[10px] text-faint font-mono tabular-nums">
        <span>0</span>
        <span>5</span>
        <span>10</span>
      </div>
    </div>
  );
}
