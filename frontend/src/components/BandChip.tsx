/** Qualitative-band chip (Strong / Solid / Mixed / Limited / Insufficient signal). */
import type { QualitativeBand } from "../types";

const TONE: Record<QualitativeBand, string> = {
  Strong: "border-band-strong text-band-strong",
  Solid: "border-band-solid text-band-solid",
  Mixed: "border-band-mixed text-band-mixed",
  Limited: "border-band-limited text-band-limited",
  "Insufficient signal": "border-band-insufficient text-band-insufficient",
};

export default function BandChip({ band }: { band: QualitativeBand }) {
  return (
    <span
      className={`inline-block rounded-full border px-2 py-0.5 text-[10px] uppercase tracking-wider ${TONE[band] ?? ""}`}
    >
      {band}
    </span>
  );
}
