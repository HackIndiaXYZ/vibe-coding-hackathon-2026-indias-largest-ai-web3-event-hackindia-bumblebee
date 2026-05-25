/**
 * App-wide top nav. Brand mark + primary destinations + accessibility toggle.
 * Stays out of the way during a session — hidden when /workspace is active
 * via App.tsx routing.
 */
import { Link, NavLink, useLocation } from "react-router-dom";

import AccessibilityToggle from "./AccessibilityToggle";

const NAV = [
  { to: "/", label: "Candidate" },
  { to: "/recruiter", label: "Recruiter" },
  { to: "/library", label: "Library" },
  { to: "/fairness", label: "Fairness" },
  { to: "/practice", label: "Practice" },
];

export default function TopNav() {
  const loc = useLocation();
  // Hide nav while a session is active (workspace/scorecard/disclosure already
  // own the chrome). Keep it on the landing/recruiter/library/etc.
  const hidden =
    loc.pathname.startsWith("/workspace/") ||
    loc.pathname.startsWith("/disclosure/") ||
    loc.pathname.startsWith("/briefing/") ||
    loc.pathname.startsWith("/scorecard/") ||
    loc.pathname.startsWith("/explanation/");
  if (hidden) return null;

  return (
    <header className="border-b border-border bg-surface/80 backdrop-blur sticky top-0 z-40">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <div className="max-w-7xl mx-auto px-4 h-[var(--layout-topnav)] flex items-center justify-between gap-4">
        <Link to="/" className="flex items-center gap-2 group">
          <span className="inline-block w-2 h-2 rounded-full bg-accent" aria-hidden />
          <span className="font-semibold text-fg group-hover:text-accent transition-colors">
            Day One
          </span>
          <span className="text-[10px] uppercase tracking-wider text-faint border border-border rounded-full px-1.5 py-0.5">
            v3
          </span>
        </Link>

        <nav className="hidden sm:flex items-center gap-1">
          {NAV.map((n) => (
            <NavLink
              key={n.to}
              to={n.to}
              end={n.to === "/"}
              className={({ isActive }) =>
                `text-sm px-3 py-1.5 rounded-md transition-colors ${
                  isActive
                    ? "bg-surface-2 text-fg"
                    : "text-muted hover:text-fg hover:bg-surface-2/60"
                }`
              }
            >
              {n.label}
            </NavLink>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          <span className="text-[10px] uppercase tracking-wider text-faint border border-border rounded-full px-2 py-0.5">
            AEDT compliant
          </span>
          <AccessibilityToggle />
        </div>
      </div>
    </header>
  );
}
