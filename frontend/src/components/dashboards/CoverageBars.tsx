import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export interface CoverageDatum {
  level: string;
  count: number;
}

const COLORS = ["#4f9cff", "#2dd4bf", "#d8b25a", "#9fb0cc", "#2f7fff", "#f2b450"];

export function CoverageBars({ data, height = 200 }: { data: CoverageDatum[]; height?: number }) {
  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 4, right: 16, bottom: 4, left: 8 }}
        >
          <XAxis type="number" hide />
          <YAxis
            type="category"
            dataKey="level"
            stroke="#5e6f8f"
            tick={{ fontSize: 12, fill: "#9fb0cc" }}
            tickLine={false}
            axisLine={false}
            width={96}
          />
          <Tooltip
            cursor={{ fill: "rgba(79,156,255,0.08)" }}
            contentStyle={{
              background: "#0d1422",
              border: "1px solid #2a3a5c",
              borderRadius: 10,
              color: "#e8eef9",
              fontSize: 12,
            }}
          />
          <Bar dataKey="count" radius={[0, 6, 6, 0]} barSize={16}>
            {data.map((_, i) => (
              <Cell key={i} fill={COLORS[i % COLORS.length]} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
