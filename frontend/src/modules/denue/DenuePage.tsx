// frontend/src/modules/denue/DenuePage.tsx
import { useEffect, useMemo, useState } from "react";

import { AppLayout } from "@/components/layout/AppLayout";
import { PageHeader } from "@/components/layout/PageHeader";
import { PreviewBanner } from "@/components/modules/PreviewBanner";
import { Card } from "@/components/ui/Card";
import { MetricCard } from "@/components/ui/MetricCard";
import { Donut, type DonutDatum } from "@/components/charts/Donut";
import { StackedBars } from "@/components/charts/StackedBars";
import { DatabaseIcon, LayersIcon, MapIcon, AnalyticsIcon } from "@/components/ui/icons";
import { getUnidades } from "./client";
import type { DenueData, SampleUnit } from "./fixtures";

const nf = new Intl.NumberFormat("es-MX");
const pct = (v: number) => `${(v * 100).toFixed(1)}%`;
const compact = new Intl.NumberFormat("es-MX", { notation: "compact", maximumFractionDigits: 1 });

export function DenuePage() {
  const [data, setData] = useState<DenueData | null>(null);

  useEffect(() => {
    let active = true;
    void getUnidades().then((d) => {
      if (active) setData(d);
    });
    return () => {
      active = false;
    };
  }, []);

  return (
    <AppLayout title="Unidades Económicas" crumb="Inteligencia Económica">
      <PageHeader
        eyebrow="Inteligencia Económica"
        title="Unidades"
        accent="Económicas"
        subtitle="Tejido económico por sector y tamaño de establecimiento como insumo para análisis territorial y de desarrollo."
        actions={<span className="pill border-line text-ink-muted">Fuente futura · INEGI DENUE</span>}
      />
      <PreviewBanner note="Datos de muestra · DENUE no está conectada (requiere token). Las cifras son ilustrativas." />

      {data ? <DenueBody data={data} /> : <LoadingState />}
    </AppLayout>
  );
}

function LoadingState() {
  return (
    <div className="reveal grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="card-premium h-28 animate-pulse p-5" />
      ))}
    </div>
  );
}

function DenueBody({ data }: { data: DenueData }) {
  const { summary, sectors, sizeBands, units } = data;

  const sectorDonut: DonutDatum[] = sectors.map((s) => ({
    name: s.sector,
    value: s.count,
    color: s.color,
  }));

  const sizeData = useMemo(
    () => sizeBands.map((b) => ({ band: b.band, establecimientos: b.count })),
    [sizeBands],
  );

  return (
    <>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Unidades económicas"
          value={nf.format(summary.total)}
          tone="accent"
          icon={<DatabaseIcon width={18} height={18} />}
          delay={0}
        />
        <MetricCard
          label="Sectores"
          value={String(summary.sectores)}
          tone="teal"
          icon={<LayersIcon width={18} height={18} />}
          delay={80}
        />
        <MetricCard
          label="Municipios"
          value={nf.format(summary.municipios)}
          tone="accent"
          icon={<MapIcon width={18} height={18} />}
          delay={160}
        />
        <MetricCard
          label="Microempresas"
          value={pct(summary.microShare)}
          tone="warning"
          icon={<AnalyticsIcon width={18} height={18} />}
          delay={240}
        />
      </div>

      <div className="mt-5 grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="reveal" style={{ animationDelay: "120ms" }}>
          <Card
            title="Unidades por sector"
            accentDot
            className="h-full"
            action={<span className="pill border-line text-ink-muted">muestra</span>}
          >
            <Donut data={sectorDonut} height={220} />
            <div className="mt-4 space-y-2">
              {sectors.map((s) => (
                <div key={s.sector} className="flex items-center justify-between gap-3 text-sm">
                  <span className="inline-flex items-center gap-2 text-ink-muted">
                    <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: s.color }} />
                    {s.sector}
                  </span>
                  <span className="font-mono tabular-nums text-ink">{compact.format(s.count)}</span>
                </div>
              ))}
            </div>
          </Card>
        </div>

        <div className="reveal" style={{ animationDelay: "200ms" }}>
          <Card
            title="Establecimientos por tamaño (empleados)"
            accentDot
            className="h-full"
            action={<span className="pill border-line text-ink-muted">muestra</span>}
          >
            <StackedBars
              data={sizeData}
              xKey="band"
              series={[{ key: "establecimientos", color: "#22d3ee" }]}
              height={240}
            />
            <div className="mt-4 flex items-center justify-between rounded-lg border border-line bg-bg-sunken px-3 py-3">
              <span className="eyebrow">Predominio micro (0–5)</span>
              <span className="font-mono text-lg tabular-nums text-state-warning">
                {pct(summary.microShare)}
              </span>
            </div>
          </Card>
        </div>
      </div>

      <UnitsTable units={units} />
    </>
  );
}

function UnitsTable({ units }: { units: SampleUnit[] }) {
  const [query, setQuery] = useState("");

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return units.filter(
      (u) =>
        u.name.toLowerCase().includes(q) ||
        u.sector.toLowerCase().includes(q) ||
        u.municipio.toLowerCase().includes(q),
    );
  }, [units, query]);

  return (
    <div className="reveal mt-5" style={{ animationDelay: "280ms" }}>
      <Card
        title="Unidades geolocalizadas (muestra)"
        accentDot
        action={<span className="pill border-line text-ink-muted">{units.length} registros</span>}
      >
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Filtrar por nombre, sector o municipio…"
            className="field-input max-w-sm"
          />
          <span className="pill border-line text-ink-muted">
            {rows.length} de {units.length}
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-line text-left">
                <th className="eyebrow py-2.5 pr-2">Unidad</th>
                <th className="eyebrow py-2.5 pr-2">Sector</th>
                <th className="eyebrow py-2.5 pr-2">Municipio</th>
                <th className="eyebrow py-2.5 pr-2 text-right">Coordenadas</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((u, i) => (
                <tr
                  key={u.id}
                  className="reveal border-b border-line/60 transition-colors hover:bg-panel-hover"
                  style={{ animationDelay: `${40 + i * 25}ms` }}
                >
                  <td className="py-2.5 pr-2 text-ink">{u.name}</td>
                  <td className="py-2.5 pr-2 text-ink-muted">{u.sector}</td>
                  <td className="py-2.5 pr-2 text-ink-muted">{u.municipio}</td>
                  <td className="py-2.5 pr-2 text-right font-mono text-xs tabular-nums text-ink-faint">
                    {u.lat.toFixed(4)}, {u.lng.toFixed(4)}
                  </td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr>
                  <td colSpan={4} className="py-8 text-center text-sm text-ink-faint">
                    Sin coincidencias para “{query}”.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
