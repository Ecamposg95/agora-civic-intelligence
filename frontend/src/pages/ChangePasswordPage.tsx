import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";

import { changeMyPassword } from "@/api/users";
import { Button } from "@/components/ui/Button";
import { LogoMark, ShieldIcon } from "@/components/ui/icons";
import { useAuthStore } from "@/store/authStore";

export function ChangePasswordPage() {
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const loadCurrentUser = useAuthStore((s) => s.loadCurrentUser);

  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const forced = Boolean(user?.must_change_password);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (next.length < 8) {
      setError("La nueva contraseña debe tener al menos 8 caracteres.");
      return;
    }
    if (next !== confirm) {
      setError("Las contraseñas no coinciden.");
      return;
    }
    setLoading(true);
    try {
      await changeMyPassword(current, next);
      await loadCurrentUser(true);
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo cambiar la contraseña");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grid min-h-screen place-items-center bg-bg px-6 py-12">
      <div className="w-full max-w-md">
        <div className="mb-6 flex items-center gap-3">
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

        <div className="panel p-8">
          <div className="eyebrow">Seguridad</div>
          <h2 className="mt-2 text-xl font-semibold tracking-tight text-ink">
            {forced ? "Cambia tu contraseña temporal" : "Cambiar contraseña"}
          </h2>
          {forced && (
            <p className="mt-2 flex items-start gap-2 rounded-lg border border-state-warning/30 bg-state-warning/10 px-3 py-2 text-sm text-state-warning">
              <ShieldIcon width={16} height={16} className="mt-0.5 shrink-0" />
              Por seguridad, debes establecer una contraseña nueva antes de continuar.
            </p>
          )}

          <form className="mt-6 space-y-4" onSubmit={handleSubmit}>
            <div>
              <label className="field-label" htmlFor="current">
                Contraseña actual
              </label>
              <input
                id="current"
                type="password"
                className="field-input"
                value={current}
                onChange={(e) => setCurrent(e.target.value)}
                required
              />
            </div>
            <div>
              <label className="field-label" htmlFor="next">
                Nueva contraseña
              </label>
              <input
                id="next"
                type="password"
                className="field-input"
                value={next}
                onChange={(e) => setNext(e.target.value)}
                required
              />
            </div>
            <div>
              <label className="field-label" htmlFor="confirm">
                Confirmar nueva contraseña
              </label>
              <input
                id="confirm"
                type="password"
                className="field-input"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                required
              />
            </div>

            {error && (
              <div className="rounded-lg border border-state-critical/40 bg-state-critical/10 px-3 py-2 text-sm text-state-critical">
                {error}
              </div>
            )}

            <Button type="submit" variant="primary" className="w-full" disabled={loading}>
              {loading ? "Guardando…" : "Actualizar contraseña"}
            </Button>
          </form>
        </div>
      </div>
    </div>
  );
}
