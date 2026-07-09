// frontend/src/modules/scrum/SprintsPage.tsx
import { useState } from "react";

import { AppLayout } from "@/components/layout/AppLayout";
import { PageHeader } from "@/components/layout/PageHeader";
import { DataState } from "@/components/ui/DataState";
import { SkeletonRows } from "@/components/ui/SkeletonCard";
import { useAsync } from "@/hooks/useAsync";
import { SCRUM_GOV } from "@/modules/registry";
import { useAuthStore } from "@/store/authStore";
import { activarSprint, cerrarSprint, createSprint, listSprints } from "@/api/scrum";

const ESTADO_LABEL: Record<string, string> = {
  PLANIFICACION: "Planificación",
  ACTIVO: "Activo",
  CERRADO: "Cerrado",
};
const ESTADO_CLASS: Record<string, string> = {
  PLANIFICACION: "border-line bg-panel-hover text-ink-faint",
  ACTIVO: "border-teal/30 bg-teal/10 text-teal",
  CERRADO: "border-line bg-panel-hover text-ink-muted",
};

const toIsoDate = (d: Date) => d.toISOString().slice(0, 10);
const today = () => toIsoDate(new Date());
const inTwoWeeks = () => {
  const d = new Date();
  d.setDate(d.getDate() + 14);
  return toIsoDate(d);
};

const EMPTY_FORM = { nombre: "", objetivo: "", fecha_inicio: today(), fecha_fin: inTwoWeeks() };

/**
 * Sprint governance — list + create (nombre/objetivo/fechas) and, per sprint,
 * activar/cerrar. Only one ACTIVO sprint per campaña — the backend 409s a
 * second activation attempt, surfaced here as "ya hay un sprint activo".
 * Create/activar/cerrar are SCRUM_GOV-only (coordinador/admin); everyone in
 * the read tier can browse the list.
 */
export function SprintsPage() {
  const role = useAuthStore((s) => s.user?.role);
  const canGovern = role ? SCRUM_GOV.includes(role) : false;

  const state = useAsync(() => listSprints({ limit: 100, offset: 0 }), []);
  const sprints = state.data?.items ?? [];

  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const [actionError, setActionError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  async function submitCreate() {
    if (!form.nombre.trim() || !form.fecha_inicio || !form.fecha_fin) return;
    setSaving(true);
    setFormError(null);
    try {
      await createSprint({
        nombre: form.nombre.trim(),
        objetivo: form.objetivo.trim() || undefined,
        fecha_inicio: form.fecha_inicio,
        fecha_fin: form.fecha_fin,
      });
      setForm(EMPTY_FORM);
      setShowForm(false);
      state.reload();
    } catch (e: unknown) {
      const status = (e as Error & { status?: number }).status;
      setFormError(
        status === 409
          ? "Ya hay un sprint activo en la campaña."
          : e instanceof Error
            ? e.message
            : "No se pudo crear el sprint.",
      );
    } finally {
      setSaving(false);
    }
  }

  async function activar(id: string) {
    setBusyId(id);
    setActionError(null);
    try {
      await activarSprint(id);
      state.reload();
    } catch (e: unknown) {
      const status = (e as Error & { status?: number }).status;
      setActionError(
        status === 409
          ? "Ya hay un sprint activo en la campaña."
          : e instanceof Error
            ? e.message
            : "No se pudo activar el sprint.",
      );
    } finally {
      setBusyId(null);
    }
  }

  async function cerrar(id: string) {
    setBusyId(id);
    setActionError(null);
    try {
      await cerrarSprint(id);
      state.reload();
    } catch (e: unknown) {
      setActionError(e instanceof Error ? e.message : "No se pudo cerrar el sprint.");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <AppLayout title="Sprints" crumb="Ciudadanía">
      <PageHeader
        eyebrow="Ciudadanía"
        title="Sprints"
        accent="Scrum"
        subtitle="Planifica, activa y cierra los sprints de la campaña — solo uno puede estar activo a la vez."
        actions={
          canGovern ? (
            <button type="button" className="btn-primary focus-ring" onClick={() => setShowForm((v) => !v)}>
              {showForm ? "Cancelar" : "Nuevo sprint"}
            </button>
          ) : undefined
        }
      />

      {actionError && (
        <div className="card-premium mb-4 px-3.5 py-2.5 text-sm text-state-critical">{actionError}</div>
      )}

      {showForm && canGovern && (
        <div className="card-premium reveal mb-5 flex flex-col gap-3 p-4">
          {formError && <p className="text-sm text-state-critical">{formError}</p>}
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <label className="flex flex-col gap-1 lg:col-span-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-ink-muted">Nombre *</span>
              <input
                className="field-input h-10"
                value={form.nombre}
                onChange={(e) => setForm((f) => ({ ...f, nombre: e.target.value }))}
                placeholder="Sprint 1 — semana 12"
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-xs font-semibold uppercase tracking-wider text-ink-muted">Inicio *</span>
              <input
                type="date"
                className="field-input h-10"
                value={form.fecha_inicio}
                onChange={(e) => setForm((f) => ({ ...f, fecha_inicio: e.target.value }))}
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className="text-xs font-semibold uppercase tracking-wider text-ink-muted">Fin *</span>
              <input
                type="date"
                className="field-input h-10"
                value={form.fecha_fin}
                onChange={(e) => setForm((f) => ({ ...f, fecha_fin: e.target.value }))}
              />
            </label>
            <label className="flex flex-col gap-1 lg:col-span-4">
              <span className="text-xs font-semibold uppercase tracking-wider text-ink-muted">Objetivo</span>
              <input
                className="field-input h-10"
                value={form.objetivo}
                onChange={(e) => setForm((f) => ({ ...f, objetivo: e.target.value }))}
                placeholder="Qué se busca lograr en este sprint…"
              />
            </label>
          </div>
          <div className="flex justify-end">
            <button
              type="button"
              className="btn-primary focus-ring disabled:cursor-not-allowed disabled:opacity-40"
              disabled={saving || !form.nombre.trim()}
              onClick={submitCreate}
            >
              {saving ? "Guardando…" : "Crear sprint"}
            </button>
          </div>
        </div>
      )}

      <DataState
        loading={state.loading}
        error={state.error}
        onRetry={state.reload}
        isEmpty={!state.loading && !state.error && sprints.length === 0}
        emptyMessage="Sin sprints registrados todavía."
        skeleton={
          <div className="card-premium p-4">
            <SkeletonRows rows={4} />
          </div>
        }
      >
        <ul className="flex flex-col gap-3">
          {sprints.map((s) => (
            <li key={s.id} className="card-premium flex flex-wrap items-center justify-between gap-3 p-4">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <p className="font-medium text-ink">{s.nombre}</p>
                  <span className={`pill ${ESTADO_CLASS[s.estado] ?? "border-line bg-panel-hover text-ink-faint"}`}>
                    {ESTADO_LABEL[s.estado] ?? s.estado}
                  </span>
                </div>
                {s.objetivo && <p className="mt-1 text-sm text-ink-muted">{s.objetivo}</p>}
                <p className="mt-1 font-mono text-xs text-ink-faint">
                  {s.fecha_inicio} → {s.fecha_fin}
                </p>
              </div>
              {canGovern && (s.estado === "PLANIFICACION" || s.estado === "ACTIVO") && (
                <div className="flex shrink-0 gap-2">
                  {s.estado === "PLANIFICACION" && (
                    <button
                      type="button"
                      className="btn-ghost focus-ring disabled:cursor-not-allowed disabled:opacity-40"
                      disabled={busyId === s.id}
                      onClick={() => activar(s.id)}
                    >
                      Activar
                    </button>
                  )}
                  {s.estado === "ACTIVO" && (
                    <button
                      type="button"
                      className="btn-ghost focus-ring disabled:cursor-not-allowed disabled:opacity-40"
                      disabled={busyId === s.id}
                      onClick={() => cerrar(s.id)}
                    >
                      Cerrar
                    </button>
                  )}
                </div>
              )}
            </li>
          ))}
        </ul>
      </DataState>
    </AppLayout>
  );
}

export default SprintsPage;
