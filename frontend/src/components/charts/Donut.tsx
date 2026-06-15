// frontend/src/components/charts/Donut.tsx
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

export interface DonutDatum { name: string; value: number; color?: string; }
const PALETTE = ["#22d3ee", "#f5b53d", "#2dd4bf", "#7c8aa5", "#06b6d4", "#f4607a"];

export function Donut({ data, height = 200 }: { data: DonutDatum[]; height?: number }) {
  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer>
        <PieChart>
          <Pie data={data} dataKey="value" nameKey="name" innerRadius="58%" outerRadius="82%" paddingAngle={2} stroke="none">
            {data.map((d, i) => <Cell key={d.name} fill={d.color ?? PALETTE[i % PALETTE.length]} />)}
          </Pie>
          <Tooltip contentStyle={{ background: "#06090c", border: "1px solid #223a44", borderRadius: 10, color: "#e6f2f5", fontSize: 12 }} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
