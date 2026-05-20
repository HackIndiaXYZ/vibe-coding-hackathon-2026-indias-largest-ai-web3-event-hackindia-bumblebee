/**
 * Channel switcher (left rail). Three Slack-style channels: #pm, #reviewer,
 * #teammate. Each shows the persona name + an unread dot when there are
 * unread messages in an inactive channel.
 */
import type { Cast, Channel, ChatMessage } from "../types";
import { CHANNELS } from "../types";

interface Props {
  cast: Cast | null;
  active: Channel;
  channels: Record<Channel, ChatMessage[]>;
  unread: Record<Channel, number>;
  onSelect: (c: Channel) => void;
}

const CHANNEL_ACCENT: Record<Channel, string> = {
  pm: "text-pm",
  reviewer: "text-reviewer",
  teammate: "text-teammate",
};

export default function ChannelList({ cast, active, channels, unread, onSelect }: Props) {
  return (
    <nav aria-label="Chat channels" className="flex flex-col">
      <p className="text-xs uppercase tracking-wider text-faint px-3 pt-3 pb-2">Channels</p>
      <ul className="flex flex-col">
        {CHANNELS.map((ch) => {
          const persona = cast?.[ch];
          const lastMsg = channels[ch].at(-1);
          const isActive = ch === active;
          const u = unread[ch] ?? 0;
          return (
            <li key={ch}>
              <button
                type="button"
                onClick={() => onSelect(ch)}
                className={[
                  "w-full text-left px-3 py-2 flex items-start gap-2 transition-colors",
                  isActive
                    ? "bg-surface-2 border-l-2 border-accent"
                    : "border-l-2 border-transparent hover:bg-surface-2/60",
                ].join(" ")}
              >
                <span className={`mt-0.5 font-mono text-sm ${CHANNEL_ACCENT[ch]}`}>#</span>
                <span className="flex-1 min-w-0">
                  <span className="flex items-baseline gap-2">
                    <span className="text-sm font-medium text-fg truncate">{ch}</span>
                    {persona && (
                      <span className="text-xs text-faint truncate">{persona.name}</span>
                    )}
                    {u > 0 && !isActive && (
                      <span className="ml-auto inline-block min-w-[1.25rem] text-center text-[10px] font-semibold rounded-full bg-accent text-black px-1.5 py-0.5">
                        {u}
                      </span>
                    )}
                  </span>
                  {lastMsg && (
                    <span className="block text-xs text-muted truncate mt-0.5">
                      {lastMsg.kind === "requirement_change" ? "⚡ " : ""}
                      {lastMsg.content}
                    </span>
                  )}
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
