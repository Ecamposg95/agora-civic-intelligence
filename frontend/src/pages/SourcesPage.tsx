import { FormEvent, useEffect, useState } from "react";

import { getSources, searchDatasets } from "@/api/sources";
import { AppLayout } from "@/components/layout/AppLayout";
import { Card } from "@/components/ui/Card";
import { SearchIcon } from "@/components/ui/icons";
import type { DatasetSummary, SourceInfo } from "@/types/sources";

const KIND_BADGE: Record<string, string> = {
  api: "border-accent/30 bg-accent/10 text-accent",
  wms: "border-teal/30 bg-teal/10 text-teal",
  download: "border-state-warning/30 bg-state-warning/10 text-state-warning",
  portal: "border-line text-ink-muted",
};

export function SourcesPage() {
  const [sources, setSources] = useState<SourceInfo[]>([]);
  const [error, setError] = useState<string | null>(null);

  const [query, setQuery] = useState("");
  const [datasets, setDatasets] = useState<DatasetSummary[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  useEffect(() => {
    getSources()
      .then(setSources)
      .catch((e) => setError(e.message));
  }, []);

  const onSearch = async (e: FormEvent) => {
    e.preventDefault();
    setSearching(true);
    setSearchError(null);
    try {
      setDatasets(await searchDatasets(query));
    } catch (err) {
      setSearchError(
        err instanceof Error ? err.message : "No se pudo consultar el catálogo",
      );
      setDatasets([]);
    } finally {
      setSearching(false);
    }
  };

  return (
    <AppLayout title="Fuentes de datos" crumb="Integraciones · INE México">
      <div className="mb-6">
        <div className="eyebrow">Integraciones</div>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-ink">
          Fuentes de datos INE
        </h1>
        <p className="mt-1 max-w-2xl text-sm text-ink-muted">
          Catálogo de fuentes consumibles del Instituto Nacional Electoral y datos
          abiertos relacionados. Consulta el catálogo de datos.gob.mx en vivo.
        </p>
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-state-critical/40 bg-state-critical/10 px-3 py-2 text-sm text-state-critical">
          {error}
        </div>
      )}

      {/* Source registry */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {sources.map((s) => (
          <div key={s.id} className="panel p-5">
            <div className="flex items-start justify-between gap-2">
              <h3 className="text-sm font-semibold text-ink">{s.name}</h3>
              <span className={`pill ${KIND_BADGE[s.kind] ?? "border-line"}`}>{s.kind}</span>
            </div>
            <p className="mt-2 text-xs leading-relaxed text-ink-muted">{s.notes}</p>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {s.formats.map((f) => (
                <span key={f} className="pill border-line text-ink-faint">
                  {f}
                </span>
              ))}
            </div>
            <div className="mt-3 flex items-center justify-between text-[11px] text-ink-faint">
              <span className="truncate">{s.base_url}</span>
              {s.auth_required && <span className="text-state-warning">requiere acceso</span>}
            </div>
          </div>
        ))}
        {sources.length === 0 && !error && (
          <div className="panel p-5 text-sm text-ink-faint">Cargando fuentes…</div>
        )}
      </div>

      {/* CKAN dataset search */}
      <div className="mt-6">
        <Card title="Catálogo datos.gob.mx (CKAN)">
          <form onSubmit={onSearch} className="relative">
            <SearchIcon className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-faint" />
            <input
              className="field-input pl-9"
              placeholder="Buscar datasets del INE (p. ej. lista nominal)…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </form>

          {searchError && (
            <div className="mt-3 rounded-lg border border-state-critical/40 bg-state-critical/10 px-3 py-2 text-sm text-state-critical">
              {searchError}
            </div>
          )}

          <div className="mt-4 space-y-2">
            {searching && (
              <div className="h-16 animate-pulse rounded-lg bg-panel-hover" />
            )}
            {!searching &&
              datasets?.map((d) => (
                <div
                  key={d.id}
                  className="flex items-start justify-between gap-3 rounded-lg border border-line bg-bg-sunken px-3 py-2.5"
                >
                  <div className="min-w-0">
                    <div className="truncate text-sm text-ink">{d.title}</div>
                    {d.organization && (
                      <div className="text-xs text-ink-faint">{d.organization}</div>
                    )}
                  </div>
                  <div className="flex shrink-0 flex-wrap justify-end gap-1.5">
                    {d.formats.slice(0, 4).map((f) => (
                      <span key={f} className="pill border-line text-ink-faint">
                        {f}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            {!searching && datasets && datasets.length === 0 && !searchError && (
              <p className="text-sm text-ink-faint">Sin resultados.</p>
            )}
            {!searching && datasets === null && (
              <p className="text-sm text-ink-faint">
                Escribe una consulta para buscar en el catálogo en vivo.
              </p>
            )}
          </div>
        </Card>
      </div>
    </AppLayout>
  );
}
