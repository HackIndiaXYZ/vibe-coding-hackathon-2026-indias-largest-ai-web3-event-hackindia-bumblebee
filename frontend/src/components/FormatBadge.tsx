/**
 * Compact chip identifying the session format.
 */
import type { SessionFormat } from "../types";

interface Props {
  format: SessionFormat;
  size?: "sm" | "md";
  practice?: boolean;
}

export default function FormatBadge({ format, size = "sm", practice = false }: Props) {
  const isA = format === "A";
  const label = isA ? "Format A · Simulation" : "Format B · Solo coding";
  const tone = isA
    ? "border-format-a text-format-a"
    : "border-format-b text-format-b";
  const px = size === "md" ? "px-2.5 py-1 text-xs" : "px-2 py-0.5 text-[10px]";
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border ${tone} ${px} bg-surface/60`}
    >
      <span aria-hidden>{isA ? "◆" : "▪"}</span>
      <span className="uppercase tracking-wider font-medium">{label}</span>
      {practice && (
        <span className="text-faint normal-case font-normal">· practice</span>
      )}
    </span>
  );
}
