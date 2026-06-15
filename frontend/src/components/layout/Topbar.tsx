import { Link, useNavigate } from "react-router-dom";

import { LogoutIcon } from "@/components/ui/icons";
import { useAuthStore } from "@/store/authStore";

interface TopbarProps {
  title: string;
  crumb?: string;
}

export function Topbar({ title, crumb }: TopbarProps) {
  const navigate = useNavigate();
  const logout = useAuthStore((s) => s.logout);
  const user = useAuthStore((s) => s.user);

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const initials = user?.full_name
    ? user.full_name
        .split(" ")
        .map((p) => p[0])
        .slice(0, 2)
        .join("")
        .toUpperCase()
    : "AT";

  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-line bg-panel/60 px-8">
      <div>
        <div className="text-base font-semibold tracking-tight text-ink">
          {title}
        </div>
        {crumb && <div className="text-xs text-ink-faint">{crumb}</div>}
      </div>

      <div className="flex items-center gap-3">
        <span className="pill border-teal/30 bg-teal/10 text-teal">
          <span className="h-1.5 w-1.5 rounded-full bg-teal" />
          Systems operational
        </span>
        <button className="btn-ghost" onClick={handleLogout}>
          <LogoutIcon width={16} height={16} />
          Sign out
        </button>
        <Link
          to="/profile"
          title="Mi perfil"
          className="grid h-9 w-9 place-items-center rounded-full border border-line bg-panel-raised text-xs font-semibold text-ink-muted transition-colors hover:border-accent hover:text-ink"
        >
          {initials}
        </Link>
      </div>
    </header>
  );
}
