import { NavLink } from "react-router-dom";

import {
  AiIcon,
  AnalyticsIcon,
  DashboardIcon,
  DatabaseIcon,
  LogoMark,
  MapIcon,
  SettingsIcon,
  VotersIcon,
} from "@/components/ui/icons";
import { useAuthStore } from "@/store/authStore";

const NAV = [
  { to: "/", label: "Command Center", icon: DashboardIcon, end: true },
  { to: "/maps", label: "Map Explorer", icon: MapIcon },
  { to: "/analytics", label: "Participation Analytics", icon: AnalyticsIcon },
  { to: "/sources", label: "Fuentes de datos", icon: DatabaseIcon },
];

const navItem =
  "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors";

const sectionLabel =
  "mt-7 mb-2 px-3 text-[10px] font-semibold uppercase tracking-[0.18em] text-ink-faint";

export function Sidebar() {
  const role = useAuthStore((s) => s.user?.role);
  const canManageUsers = role === "admin" || role === "superadmin";

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `${navItem} ${
      isActive
        ? "bg-accent/10 text-accent"
        : "text-ink-muted hover:bg-panel-hover hover:text-ink"
    }`;

  return (
    <aside className="flex w-64 shrink-0 flex-col border-r border-line bg-panel px-4 py-5">
      <div className="flex items-center gap-3 px-2">
        <div className="grid h-9 w-9 place-items-center rounded-lg bg-accent/15 text-accent">
          <LogoMark width={20} height={20} />
        </div>
        <div>
          <div className="text-sm font-semibold tracking-tight text-ink">Ágora</div>
          <div className="text-[11px] uppercase tracking-[0.16em] text-ink-faint">
            Civic Intelligence
          </div>
        </div>
      </div>

      <div className={sectionLabel}>Platform</div>
      <nav className="flex flex-col gap-1">
        {NAV.map(({ to, label, icon: Icon, end }) => (
          <NavLink key={to} to={to} end={end} className={linkClass}>
            <Icon width={18} height={18} />
            {label}
          </NavLink>
        ))}
      </nav>

      {canManageUsers && (
        <>
          <div className={sectionLabel}>Administración</div>
          <nav className="flex flex-col gap-1">
            <NavLink to="/users" className={linkClass}>
              <VotersIcon width={18} height={18} />
              Usuarios
            </NavLink>
            <NavLink to="/organization" className={linkClass}>
              <SettingsIcon width={18} height={18} />
              Organización
            </NavLink>
          </nav>
        </>
      )}

      <div className={sectionLabel}>Intelligence</div>
      <div className={`${navItem} cursor-not-allowed text-ink-faint`} aria-disabled="true">
        <AiIcon width={18} height={18} />
        AI Analyst
        <span className="pill ml-auto border-teal/30 bg-teal/10 text-teal">Soon</span>
      </div>

      <div className="mt-auto px-3 pt-6 text-[11px] leading-relaxed text-ink-faint">
        Atlas Tech · GovTech
        <br />
        <span className="opacity-70">v0.1.0 · MVP scaffold</span>
      </div>
    </aside>
  );
}
