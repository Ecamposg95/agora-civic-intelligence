import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { CHART_TOOLTIP_STYLE } from "@/constants/ui";

export interface CoverageDatum {
  level: string;
  count: number;
}

const COLORS = ["#22d3ee", "#2dd4bf", "#f5b53d", "#8ba0a8", "#06b6d4", "#f5b53d"];

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
            stroke="#52646d"
            tick={{ fontSize: 12, fill: "#8ba0a8" }}
            tickLine={false}
            axisLine={false}
            width={96}
          />
          <Tooltip
            cursor={{ fill: "rgba(34,211,238,0.08)" }}
            contentStyle={CHART_TOOLTIP_STYLE}
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
