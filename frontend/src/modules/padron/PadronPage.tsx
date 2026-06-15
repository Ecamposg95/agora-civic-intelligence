// frontend/src/modules/padron/PadronPage.tsx
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { AppLayout } from "@/components/layout/AppLayout";
import { PreviewBanner } from "@/components/modules/PreviewBanner";
import { Card } from "@/components/ui/Card";
import { MetricCard } from "@/components/ui/MetricCard";
import { AGE_BANDS, SUMMARY, TOP_ENTITIES } from "./fixtures";

const nf = new Intl.NumberFormat("es-MX");
const pct = (v: number) => `${(v * 100).toFixed(1)}%`;

export function PadronPage() {
  return (
    <AppLayout title="Padrón / Lista Nominal" crumb="Inteligencia Electoral">
      <PreviewBanner />
      <div className="mb-5 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Padrón electoral" value={nf.format(SUMMARY.padron)} />
        <MetricCard label="Lista nominal" value={nf.format(SUMMARY.listaNominal)} />
        <MetricCard label="Cobertura" value={pct(SUMMARY.cobertura)} />
        <MetricCard label="Edad mediana" value={`${SUMMARY.edadMediana} años`} />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card title="Distribución por edad y sexo (%)">
          <div style={{ width: "100%", height: 280 }}>
            <ResponsiveContainer>
              <BarChart data={AGE_BANDS} margin={{ left: -16 }}>
                <XAxis dataKey="band" stroke="#5e6f8f" tick={{ fontSize: 12 }} />
                <YAxis stroke="#5e6f8f" tick={{ fontSize: 12 }} />
                <Tooltip contentStyle={{ background: "#0d1422", border: "1px solid #2a3a5c", borderRadius: 10 }} />
                <Bar dataKey="hombres" fill="#4f9cff" radius={[4, 4, 0, 0]} />
                <Bar dataKey="mujeres" fill="#2dd4bf" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card title="Padrón por entidad (top 5)">
          <div className="space-y-2">
            {TOP_ENTITIES.map((e) => (
              <div key={e.entity} className="flex items-center justify-between rounded-lg border border-line bg-bg-sunken px-3 py-2.5">
                <span className="text-sm text-ink">{e.entity}</span>
                <span className="text-sm text-ink-muted">{nf.format(e.padron)}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </AppLayout>
  );
}
