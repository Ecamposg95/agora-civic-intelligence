import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { assignTerritory, searchAreas, type AreaHit } from "@/api/territory";
import {
  createUser,
  deleteUser,
  listUsers,
  resetPassword,
  restoreUser,
  setActive,
  updateUser,
} from "@/api/users";
import { AppLayout } from "@/components/layout/AppLayout";
import { PageHeader } from "@/components/layout/PageHeader";
import { AnimatedNumber } from "@/components/ui/AnimatedNumber";
import { Button } from "@/components/ui/Button";
import { DataState } from "@/components/ui/DataState";
import { DataTable, type Column } from "@/components/ui/DataTable";
import { Modal } from "@/components/ui/Modal";
import { SearchIcon, UserIcon } from "@/components/ui/icons";
import { ROLE_BADGE, TONE_BADGE } from "@/constants/ui";
import { useAuthStore } from "@/store/authStore";
import type { User, UserRole } from "@/types/auth";
import type { UserCreatePayload, UserUpdatePayload } from "@/types/users";

const PAGE_SIZE = 20;
const ALL_ROLES: UserRole[] = [
  "superadmin", "admin", "coordinador", "lider",
  "activista", "capturista", "analyst", "viewer", "consulta",
];

// Columns defined at module scope — render fns only reference module-level
// constants (ROLE_BADGE, TONE_BADGE), so no closure over props/state.
// This keeps DataTable's internal useMemo dep-array stable.
const USER_COLUMNS: Column<User>[] = [
  {
    key: "full_name",
    header: "Usuario",
    render: (u) => (
      <div className="flex items-center gap-3">
        <span className="metric-chip h-8 w-8 shrink-0 font-display text-[11px] font-bold text-accent">
          {u.full_name
            .trim()
            .split(/\s+/)
            .filter(Boolean)
            .slice(0, 2)
            .map((p) => p[0]?.toUpperCase() ?? "")
            .join("") || "—"}
        </span>
        <div className="min-w-0">
          <div className="truncate font-medium text-ink">{u.full_name}</div>
          <div className="truncate font-mono text-xs text-ink-faint">{u.email}</div>
        </div>
      </div>
    ),
  },
  {
    key: "role",
    header: "Rol",
    render: (u) => (
      <span className={`pill ${TONE_BADGE[ROLE_BADGE[u.role] ?? "neutral"]}`}>{u.role}</span>
    ),
  },
  {
    key: "is_active",
    header: "Estado",
    render: (u) => (
      <div className="flex flex-wrap items-center gap-1.5">
        {u.is_active ? (
          <span className={`pill ${TONE_BADGE.ok}`}>Activo</span>
        ) : (
          <span className={`pill ${TONE_BADGE.critical}`}>Inactivo</span>
        )}
        {u.must_change_password && (
          <span className={`pill ${TONE_BADGE.warning}`}>Cambio pendiente</span>
        )}
      </div>
    ),
  },
  {
    key: "phone",
    header: "Teléfono",
    hideOnCard: true,
    render: (u) => (
      <span className="font-mono text-xs text-ink-muted">{u.phone || "—"}</span>
    ),
  },
  {
    key: "area_nombre",
    header: "Territorio",
    render: (u) => (
      <span className={`pill ${TONE_BADGE[u.area_nombre ? "info" : "neutral"]}`}>
        {u.area_nombre ?? "—"}
      </span>
    ),
  },
];

type StatusFilter = "all" | "active" | "inactive";

export function UsersPage() {
  const currentUser = useAuthStore((s) => s.user);
  const isSuper = currentUser?.role === "superadmin";
  const assignableRoles = useMemo(
    () => (isSuper ? ALL_ROLES : ALL_ROLES.filter((r) => r !== "superadmin")),
    [isSuper],
  );

  const [rows, setRows] = useState<User[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [searchInput, setSearchInput] = useState("");
  const [query, setQuery] = useState("");
  const [role, setRole] = useState<UserRole | "">("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [includeDeleted, setIncludeDeleted] = useState(false);
  const [sort, setSort] = useState<"created_at" | "full_name" | "email" | "role">("created_at");
  const [order, setOrder] = useState<"asc" | "desc">("desc");
  const [offset, setOffset] = useState(0);

  // Modals
  const [createOpen, setCreateOpen] = useState(false);
  const [editing, setEditing] = useState<User | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<User | null>(null);
  const [tempPassword, setTempPassword] = useState<{ label: string; value: string } | null>(null);

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listUsers({
        q: query || undefined,
        role: role || undefined,
        is_active: statusFilter === "all" ? undefined : statusFilter === "active",
        include_deleted: includeDeleted || undefined,
        sort,
        order,
        limit: PAGE_SIZE,
        offset,
      });
      setRows(data.items);
      setTotal(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudieron cargar los usuarios");
    } finally {
      setLoading(false);
    }
  }, [query, role, statusFilter, includeDeleted, sort, order, offset]);

  useEffect(() => {
    void fetchUsers();
  }, [fetchUsers]);

  const onSearch = (e: FormEvent) => {
    e.preventDefault();
    setOffset(0);
    setQuery(searchInput.trim());
  };

  const withRefresh = useCallback(
    async (fn: () => Promise<unknown>) => {
      try {
        await fn();
        await fetchUsers();
      } catch (err) {
        setError(err instanceof Error ? err.message : "La operación falló");
      }
    },
    [fetchUsers],
  );

  // Actions column references withRefresh/setEditing/setConfirmDelete/
  // setTempPassword (all stable) and includeDeleted (boolean state).
  // useMemo keeps the array reference stable to avoid DataTable re-sorting.
  const columns = useMemo<Column<User>[]>(
    () => [
      ...USER_COLUMNS,
      {
        key: "actions",
        header: "Acciones",
        align: "right" as const,
        render: (u) => (
          <div className="flex flex-wrap justify-end gap-1.5 text-xs">
            <button
              className="rounded-md border border-line bg-bg-sunken px-2 py-1 font-medium text-accent transition-colors hover:border-accent/40 hover:bg-accent/10"
              onClick={() => setEditing(u)}
            >
              Editar
            </button>
            {u.is_active ? (
              <button
                className="rounded-md border border-line bg-bg-sunken px-2 py-1 font-medium text-ink-muted transition-colors hover:border-line-strong hover:text-ink"
                onClick={() => withRefresh(() => setActive(u.id, false))}
              >
                Desactivar
              </button>
            ) : (
              <button
                className="rounded-md border border-line bg-bg-sunken px-2 py-1 font-medium text-teal transition-colors hover:border-teal/40 hover:bg-teal/10"
                onClick={() => withRefresh(() => setActive(u.id, true))}
              >
                Activar
              </button>
            )}
            <button
              className="rounded-md border border-line bg-bg-sunken px-2 py-1 font-medium text-ink-muted transition-colors hover:border-line-strong hover:text-ink"
              onClick={() =>
                withRefresh(async () => {
                  const r = await resetPassword(u.id);
                  setTempPassword({
                    label: `Contraseña temporal para ${u.email}`,
                    value: r.temporary_password,
                  });
                })
              }
            >
              Reset clave
            </button>
            <button
              className="rounded-md border border-line bg-bg-sunken px-2 py-1 font-medium text-state-critical transition-colors hover:border-state-critical/40 hover:bg-state-critical/10"
              onClick={() => setConfirmDelete(u)}
            >
              Eliminar
            </button>
            {includeDeleted && (
              <button
                className="rounded-md border border-line bg-bg-sunken px-2 py-1 font-medium text-teal transition-colors hover:border-teal/40 hover:bg-teal/10"
                onClick={() => withRefresh(() => restoreUser(u.id))}
              >
                Restaurar
              </button>
            )}
          </div>
        ),
      },
    ],
    [includeDeleted, withRefresh],
  );

  const page = Math.floor(offset / PAGE_SIZE) + 1;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <AppLayout title="Usuarios" crumb="Administración · Control de acceso">
      <PageHeader
        eyebrow="Administración"
        title="Gestión de"
        accent="usuarios"
        subtitle="Alta, roles, estado y restablecimiento de contraseñas. Acciones tenant-scoped y auditadas."
        actions={
          <>
            <div className="card-premium px-4 py-3">
              <div className="eyebrow mb-1.5">Usuarios</div>
              <div className="flex items-center gap-2">
                <UserIcon className="h-5 w-5 text-accent" />
                <AnimatedNumber
                  value={total}
                  className="font-display text-2xl font-bold tabular-nums text-ink"
                />
              </div>
            </div>
            <Button
              variant="primary"
              className="shadow-glow-accent"
              onClick={() => setCreateOpen(true)}
            >
              + Nuevo usuario
            </Button>
          </>
        }
      />

      {/* Toolbar */}
      <div className="reveal card-premium mb-4 flex flex-wrap items-center gap-3 p-4" style={{ animationDelay: "120ms" }}>
        <form onSubmit={onSearch} className="relative flex-1 min-w-[220px]">
          <SearchIcon className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-faint" />
          <input
            className="field-input pl-9"
            placeholder="Buscar por nombre o email…"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
          />
        </form>
        <select
          className="field-input w-auto"
          value={role}
          onChange={(e) => {
            setOffset(0);
            setRole(e.target.value as UserRole | "");
          }}
        >
          <option value="">Todos los roles</option>
          {ALL_ROLES.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
        <select
          className="field-input w-auto"
          value={statusFilter}
          onChange={(e) => {
            setOffset(0);
            setStatusFilter(e.target.value as StatusFilter);
          }}
        >
          <option value="all">Todos los estados</option>
          <option value="active">Activos</option>
          <option value="inactive">Inactivos</option>
        </select>
        <select
          className="field-input w-auto"
          value={`${sort}:${order}`}
          onChange={(e) => {
            const [s, o] = e.target.value.split(":");
            setSort(s as typeof sort);
            setOrder(o as typeof order);
          }}
        >
          <option value="created_at:desc">Más recientes</option>
          <option value="created_at:asc">Más antiguos</option>
          <option value="full_name:asc">Nombre A–Z</option>
          <option value="email:asc">Email A–Z</option>
          <option value="role:asc">Rol</option>
        </select>
        <label className="flex cursor-pointer items-center gap-2 text-sm text-ink-muted">
          <input
            type="checkbox"
            className="h-4 w-4 rounded border-line bg-bg-sunken accent-accent"
            checked={includeDeleted}
            onChange={(e) => {
              setOffset(0);
              setIncludeDeleted(e.target.checked);
            }}
          />
          Incluir eliminados
        </label>
      </div>

      {/* Table — DataState handles loading skeleton, error card, and empty state */}
      <div className="reveal" style={{ animationDelay: "200ms" }}>
        <DataState
          loading={loading}
          error={error}
          onRetry={fetchUsers}
          isEmpty={rows.length === 0}
          emptyMessage="Sin usuarios para los filtros actuales."
        >
          <DataTable
            columns={columns}
            rows={rows}
            rowKey={(u) => u.id}
            pageSize={PAGE_SIZE}
          />
        </DataState>
      </div>

      {/* Pagination */}
      <div className="mt-4 flex items-center justify-between text-sm text-ink-muted">
        <span>
          {total} usuario{total === 1 ? "" : "s"} · página {page} de {pages}
        </span>
        <div className="flex gap-2">
          <Button
            onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            disabled={offset === 0}
          >
            Anterior
          </Button>
          <Button
            onClick={() => setOffset(offset + PAGE_SIZE)}
            disabled={offset + PAGE_SIZE >= total}
          >
            Siguiente
          </Button>
        </div>
      </div>

      {/* Create modal */}
      <CreateUserModal
        open={createOpen}
        roles={assignableRoles}
        onClose={() => setCreateOpen(false)}
        onCreated={(label, value) => {
          setCreateOpen(false);
          if (value) setTempPassword({ label, value });
          void fetchUsers();
        }}
      />

      {/* Edit modal */}
      <EditUserModal
        user={editing}
        roles={assignableRoles}
        isSuper={isSuper}
        onClose={() => setEditing(null)}
        onSaved={() => {
          setEditing(null);
          void fetchUsers();
        }}
        onTerritoryAssigned={fetchUsers}
      />

      {/* Delete confirm */}
      <Modal
        open={Boolean(confirmDelete)}
        title="Eliminar usuario"
        onClose={() => setConfirmDelete(null)}
        footer={
          <>
            <Button onClick={() => setConfirmDelete(null)}>Cancelar</Button>
            <Button
              variant="primary"
              onClick={() =>
                withRefresh(async () => {
                  if (confirmDelete) await deleteUser(confirmDelete.id);
                  setConfirmDelete(null);
                })
              }
            >
              Eliminar
            </Button>
          </>
        }
      >
        <p className="text-sm text-ink-muted">
          Se aplicará un borrado lógico (soft-delete) a{" "}
          <span className="text-ink">{confirmDelete?.email}</span>. Podrás
          restaurarlo después con el filtro “Incluir eliminados”.
        </p>
      </Modal>

      {/* Temp password reveal */}
      <Modal
        open={Boolean(tempPassword)}
        title="Contraseña temporal"
        onClose={() => setTempPassword(null)}
        footer={<Button variant="primary" onClick={() => setTempPassword(null)}>Listo</Button>}
      >
        <p className="text-sm text-ink-muted">{tempPassword?.label}</p>
        <div className="mt-3 select-all rounded-lg border border-line bg-bg-sunken px-3 py-2.5 font-mono text-sm text-ink">
          {tempPassword?.value}
        </div>
        <p className="mt-2 text-xs text-ink-faint">
          Cópiala ahora: no se volverá a mostrar. El usuario deberá cambiarla al
          iniciar sesión.
        </p>
      </Modal>
    </AppLayout>
  );
}

/* ----------------------------- Create modal ----------------------------- */
function CreateUserModal({
  open,
  roles,
  onClose,
  onCreated,
}: {
  open: boolean;
  roles: UserRole[];
  onClose: () => void;
  onCreated: (label: string, tempPassword: string | null) => void;
}) {
  const [form, setForm] = useState<UserCreatePayload>({
    email: "",
    full_name: "",
    role: "viewer",
    phone: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      const res = await createUser({ ...form, phone: form.phone || null });
      onCreated(`Contraseña temporal para ${res.user.email}`, res.temporary_password);
      setForm({ email: "", full_name: "", role: "viewer", phone: "" });
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo crear el usuario");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      open={open}
      title="Nuevo usuario"
      onClose={onClose}
      footer={
        <>
          <Button onClick={onClose}>Cancelar</Button>
          <Button variant="primary" type="submit" form="create-user-form" disabled={saving}>
            {saving ? "Creando…" : "Crear usuario"}
          </Button>
        </>
      }
    >
      <form id="create-user-form" className="space-y-4" onSubmit={submit}>
        <div>
          <label className="field-label">Nombre completo</label>
          <input
            className="field-input"
            value={form.full_name}
            onChange={(e) => setForm({ ...form, full_name: e.target.value })}
            required
          />
        </div>
        <div>
          <label className="field-label">Email</label>
          <input
            type="email"
            className="field-input"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            required
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="field-label">Rol</label>
            <select
              className="field-input"
              value={form.role}
              onChange={(e) => setForm({ ...form, role: e.target.value as UserRole })}
            >
              {roles.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="field-label">Teléfono (opcional)</label>
            <input
              className="field-input"
              value={form.phone ?? ""}
              onChange={(e) => setForm({ ...form, phone: e.target.value })}
            />
          </div>
        </div>
        <p className="text-xs text-ink-faint">
          Se generará una contraseña temporal; el usuario deberá cambiarla en su
          primer inicio de sesión.
        </p>
        {error && (
          <div className="rounded-lg border border-state-critical/40 bg-state-critical/10 px-3 py-2 text-sm text-state-critical">
            {error}
          </div>
        )}
      </form>
    </Modal>
  );
}

/* ------------------------------ Edit modal ------------------------------ */
function EditUserModal({
  user,
  roles,
  isSuper,
  onClose,
  onSaved,
  onTerritoryAssigned,
}: {
  user: User | null;
  roles: UserRole[];
  isSuper: boolean;
  onClose: () => void;
  onSaved: () => void;
  onTerritoryAssigned: () => Promise<void>;
}) {
  const [form, setForm] = useState<UserUpdatePayload>({});
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  // Territory assignment (superadmin only) — independent of the profile
  // form above; each pick/clear calls the API immediately and refreshes
  // the parent's user list, without closing this modal.
  const [currentArea, setCurrentArea] = useState<{ id: string; nombre: string } | null>(null);
  const [areaQuery, setAreaQuery] = useState("");
  const [areaResults, setAreaResults] = useState<AreaHit[]>([]);
  const [areaSearching, setAreaSearching] = useState(false);
  const [areaError, setAreaError] = useState<string | null>(null);
  const [assigningArea, setAssigningArea] = useState(false);

  useEffect(() => {
    if (user) {
      setForm({
        full_name: user.full_name,
        role: user.role,
        phone: user.phone ?? "",
        is_active: user.is_active,
      });
      setError(null);
      setCurrentArea(
        user.area_id && user.area_nombre
          ? { id: user.area_id, nombre: user.area_nombre }
          : null,
      );
      setAreaQuery("");
      setAreaResults([]);
      setAreaError(null);
    }
  }, [user]);

  // Debounced area search — only while the modal is in superadmin mode.
  useEffect(() => {
    if (!isSuper) return;
    const q = areaQuery.trim();
    if (!q) {
      setAreaResults([]);
      setAreaSearching(false);
      return;
    }
    setAreaSearching(true);
    const timer = setTimeout(() => {
      searchAreas(q)
        .then(setAreaResults)
        .catch((err) => setAreaError(err instanceof Error ? err.message : "No se pudo buscar"))
        .finally(() => setAreaSearching(false));
    }, 300);
    return () => clearTimeout(timer);
  }, [areaQuery, isSuper]);

  const handleAssignArea = async (hit: AreaHit) => {
    if (!user) return;
    setAssigningArea(true);
    setAreaError(null);
    try {
      await assignTerritory(user.id, hit.id);
      setCurrentArea({ id: hit.id, nombre: hit.name });
      setAreaQuery("");
      setAreaResults([]);
      await onTerritoryAssigned();
    } catch (err) {
      setAreaError(err instanceof Error ? err.message : "No se pudo asignar el territorio");
    } finally {
      setAssigningArea(false);
    }
  };

  const handleClearArea = async () => {
    if (!user) return;
    setAssigningArea(true);
    setAreaError(null);
    try {
      await assignTerritory(user.id, null);
      setCurrentArea(null);
      await onTerritoryAssigned();
    } catch (err) {
      setAreaError(err instanceof Error ? err.message : "No se pudo quitar el territorio");
    } finally {
      setAssigningArea(false);
    }
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!user) return;
    setError(null);
    setSaving(true);
    try {
      await updateUser(user.id, { ...form, phone: form.phone || null });
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo actualizar");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal
      open={Boolean(user)}
      title={`Editar ${user?.full_name ?? ""}`}
      onClose={onClose}
      footer={
        <>
          <Button onClick={onClose}>Cancelar</Button>
          <Button variant="primary" type="submit" form="edit-user-form" disabled={saving}>
            {saving ? "Guardando…" : "Guardar cambios"}
          </Button>
        </>
      }
    >
      <form id="edit-user-form" className="space-y-4" onSubmit={submit}>
        <div>
          <label className="field-label">Nombre completo</label>
          <input
            className="field-input"
            value={form.full_name ?? ""}
            onChange={(e) => setForm({ ...form, full_name: e.target.value })}
          />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="field-label">Rol</label>
            <select
              className="field-input"
              value={form.role}
              onChange={(e) => setForm({ ...form, role: e.target.value as UserRole })}
            >
              {roles.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="field-label">Teléfono</label>
            <input
              className="field-input"
              value={form.phone ?? ""}
              onChange={(e) => setForm({ ...form, phone: e.target.value })}
            />
          </div>
        </div>
        <label className="flex cursor-pointer items-center gap-2 text-sm text-ink-muted">
          <input
            type="checkbox"
            className="h-4 w-4 rounded border-line bg-bg-sunken accent-accent"
            checked={Boolean(form.is_active)}
            onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
          />
          Cuenta activa
        </label>
        {error && (
          <div className="rounded-lg border border-state-critical/40 bg-state-critical/10 px-3 py-2 text-sm text-state-critical">
            {error}
          </div>
        )}
      </form>

      {isSuper && (
        <div className="mt-4 border-t border-line pt-4">
          <label className="field-label">Territorio</label>
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <span className={`pill ${TONE_BADGE[currentArea ? "info" : "neutral"]}`}>
              {currentArea?.nombre ?? "Sin territorio asignado"}
            </span>
            {currentArea && (
              <button
                type="button"
                className="rounded-md border border-line bg-bg-sunken px-2 py-1 text-xs font-medium text-ink-muted transition-colors hover:border-state-critical/40 hover:text-state-critical"
                onClick={() => void handleClearArea()}
                disabled={assigningArea}
              >
                Quitar
              </button>
            )}
          </div>
          <input
            className="field-input"
            placeholder="Buscar área (municipio, sección…)"
            value={areaQuery}
            onChange={(e) => setAreaQuery(e.target.value)}
            disabled={assigningArea}
          />
          {areaSearching && <p className="mt-1 text-xs text-ink-faint">Buscando…</p>}
          {areaResults.length > 0 && (
            <ul className="mt-2 max-h-40 overflow-y-auto rounded-lg border border-line bg-bg-sunken">
              {areaResults.map((hit) => (
                <li key={hit.id}>
                  <button
                    type="button"
                    className="flex w-full items-center justify-between px-3 py-2 text-left text-sm text-ink transition-colors hover:bg-panel-hover"
                    onClick={() => void handleAssignArea(hit)}
                    disabled={assigningArea}
                  >
                    <span className="truncate">{hit.name}</span>
                    <span className="ml-2 shrink-0 text-xs text-ink-faint">{hit.level}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
          {areaError && <p className="mt-1 text-xs text-state-critical">{areaError}</p>}
        </div>
      )}
    </Modal>
  );
}
