// frontend/src/modules/resultados/ResultadosPage.tsx
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { AppLayout } from "@/components/layout/AppLayout";
import { PreviewBanner } from "@/components/modules/PreviewBanner";
import { Card } from "@/components/ui/Card";
import { MetricCard } from "@/components/ui/MetricCard";
import { ENTITY_RESULTS, NATIONAL, PARTY_RESULTS } from "./fixtures";

const pct = (v: number) => `${(v * 100).toFixed(1)}%`;

export function ResultadosPage() {
  return (
    <AppLayout title="Resultados Electorales" crumb="Inteligencia Electoral">
      <PreviewBanner />
      <div className="mb-5 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <MetricCard label="Participación nacional" value={pct(NATIONAL.turnout)} />
        <MetricCard label="Casillas computadas" value={pct(NATIONAL.counted)} />
        <MetricCard label="Fuerza líder" value={NATIONAL.leader} />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <Card title="Distribución del voto">
          <div style={{ width: "100%", height: 260 }}>
            <ResponsiveContainer>
              <BarChart data={PARTY_RESULTS} layout="vertical" margin={{ left: 24 }}>
                <XAxis type="number" tickFormatter={pct} stroke="#5e6f8f" tick={{ fontSize: 12 }} />
                <YAxis type="category" dataKey="party" stroke="#5e6f8f" tick={{ fontSize: 12 }} width={110} />
                <Tooltip formatter={(v: number) => pct(v)} contentStyle={{ background: "#0d1422", border: "1px solid #2a3a5c", borderRadius: 10 }} />
                <Bar dataKey="share" radius={[0, 6, 6, 0]}>
                  {PARTY_RESULTS.map((p) => <Cell key={p.party} fill={p.color} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card title="Resultados por entidad">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead><tr className="text-left text-xs uppercase tracking-wide text-ink-faint">
                <th className="px-2 py-2">Entidad</th><th className="px-2 py-2">Participación</th><th className="px-2 py-2">Ganador</th><th className="px-2 py-2">Margen</th>
              </tr></thead>
              <tbody>
                {ENTITY_RESULTS.map((e) => (
                  <tr key={e.entity} className="border-t border-line">
                    <td className="px-2 py-2 text-ink">{e.entity}</td>
                    <td className="px-2 py-2 text-ink-muted">{pct(e.turnout)}</td>
                    <td className="px-2 py-2"><span className="pill border-accent/30 bg-accent/10 text-accent">{e.winner}</span></td>
                    <td className="px-2 py-2 text-ink-muted">{pct(e.margin)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </AppLayout>
  );
}
