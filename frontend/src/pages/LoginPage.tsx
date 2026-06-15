import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/Button";
import {
  AnalyticsIcon,
  LayersIcon,
  LogoMark,
  MapIcon,
  ShieldIcon,
} from "@/components/ui/icons";
import { useAuthStore } from "@/store/authStore";

const FEATURES = [
  { icon: MapIcon, label: "Mapas electorales y territoriales" },
  { icon: AnalyticsIcon, label: "Analítica de participación" },
  { icon: LayersIcon, label: "Gobernanza de datos electorales" },
];

const STATS = [
  { value: "1.28M", label: "Padrón" },
  { value: "412", label: "Áreas" },
  { value: "63.1%", label: "Participación" },
];

export function LoginPage() {
  const navigate = useNavigate();
  const { login, loading, error } = useAuthStore();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const ok = await login(email, password);
    if (ok) navigate("/");
  };

  return (
    <div className="grid min-h-screen grid-cols-1 lg:grid-cols-2">
      {/* Left — institutional hero */}
      <aside className="relative hidden flex-col justify-between overflow-hidden bg-panel p-12 lg:flex">
        <div className="grid-backdrop pointer-events-none absolute inset-0 opacity-60" />
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-accent/10 via-transparent to-teal/10" />

        <div className="relative flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-lg bg-accent/15 text-accent">
            <LogoMark width={22} height={22} />
          </div>
          <div>
            <div className="text-sm font-semibold tracking-tight text-ink">Ágora</div>
            <div className="text-[11px] uppercase tracking-[0.16em] text-ink-faint">
              Civic Intelligence
            </div>
          </div>
        </div>

        <div className="relative max-w-md">
          <div className="eyebrow">GovTech Command Center</div>
          <h1 className="mt-4 text-3xl font-semibold leading-tight tracking-tight text-ink">
            Inteligencia cívica, electoral y territorial — gobernada de extremo a
            extremo.
          </h1>
          <p className="mt-4 text-sm leading-relaxed text-ink-muted">
            Plataforma privacy-by-design para instituciones: mapas unificados,
            dashboards ejecutivos, gobernanza de datos electorales y analítica de
            participación, con auditabilidad total.
          </p>

          <ul className="mt-6 space-y-3">
            {FEATURES.map(({ icon: Icon, label }) => (
              <li key={label} className="flex items-center gap-3 text-sm text-ink-muted">
                <span className="grid h-8 w-8 place-items-center rounded-lg border border-line bg-bg-sunken text-accent">
                  <Icon width={16} height={16} />
                </span>
                {label}
              </li>
            ))}
          </ul>

          <div className="mt-8 flex gap-6">
            {STATS.map((stat) => (
              <div key={stat.label}>
                <div className="text-xl font-semibold tracking-tight text-ink">
                  {stat.value}
                </div>
                <div className="text-[11px] uppercase tracking-wide text-ink-faint">
                  {stat.label}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="relative flex items-center gap-2 text-xs text-ink-faint">
          <ShieldIcon width={15} height={15} /> Privacy-by-design · Audit-logged ·
          Multi-tenant ready
        </div>
      </aside>

      {/* Right — sign-in card */}
      <section className="flex items-center justify-center bg-bg px-6 py-12">
        <div className="panel w-full max-w-sm p-8">
          <div className="mb-6 flex items-center gap-3 lg:hidden">
            <div className="grid h-10 w-10 place-items-center rounded-lg bg-accent/15 text-accent">
              <LogoMark width={22} height={22} />
            </div>
            <div className="text-sm font-semibold tracking-tight text-ink">
              Ágora · Civic Intelligence
            </div>
          </div>

          <div className="eyebrow">Iniciar sesión</div>
          <h2 className="mt-2 text-xl font-semibold tracking-tight text-ink">
            Acceso al command center
          </h2>
          <p className="mt-1 text-sm text-ink-muted">
            Usa tus credenciales institucionales.
          </p>

          <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
            <div>
              <label htmlFor="email" className="field-label">
                Email
              </label>
              <input
                id="email"
                type="email"
                className="field-input"
                placeholder="analyst@institution.gov"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div>
              <label htmlFor="password" className="field-label">
                Contraseña
              </label>
              <input
                id="password"
                type="password"
                className="field-input"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>

            {error && (
              <div className="rounded-lg border border-state-critical/40 bg-state-critical/10 px-3 py-2 text-sm text-state-critical">
                {error}
              </div>
            )}

            <Button type="submit" variant="primary" className="w-full" disabled={loading}>
              {loading ? "Autenticando…" : "Iniciar sesión"}
            </Button>
          </form>

          <p className="mt-5 text-center text-[11px] text-ink-faint">
            Conecta credenciales institucionales para continuar.
          </p>
        </div>
      </section>
    </div>
  );
}
