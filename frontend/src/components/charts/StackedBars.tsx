// frontend/src/components/charts/StackedBars.tsx
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export interface StackSeries { key: string; color: string; }
export function StackedBars({ data, series, xKey, height = 240 }: {
  data: Record<string, number | string>[]; series: StackSeries[]; xKey: string; height?: number;
}) {
  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer>
        <BarChart data={data} margin={{ left: -16, top: 8 }}>
          <CartesianGrid stroke="#15242b" vertical={false} />
          <XAxis dataKey={xKey} stroke="#52646d" tick={{ fontSize: 12 }} tickLine={false} axisLine={{ stroke: "#15242b" }} />
          <YAxis stroke="#52646d" tick={{ fontSize: 12 }} tickLine={false} axisLine={false} allowDecimals={false} />
          <Tooltip contentStyle={{ background: "#06090c", border: "1px solid #223a44", borderRadius: 10, color: "#e6f2f5", fontSize: 12 }} />
          {series.map((s) => <Bar key={s.key} dataKey={s.key} stackId="a" fill={s.color} radius={[2, 2, 0, 0]} />)}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
