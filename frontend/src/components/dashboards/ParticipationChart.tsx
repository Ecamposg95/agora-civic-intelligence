import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { TrendPoint } from "@/types/analytics";

interface ParticipationChartProps {
  data: TrendPoint[];
  height?: number;
}

const pct = (v: number) => `${(v * 100).toFixed(0)}%`;

export function ParticipationChart({ data, height = 220 }: ParticipationChartProps) {
  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 10, right: 8, bottom: 0, left: -16 }}>
          <defs>
            <linearGradient id="participationFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#4f9cff" stopOpacity={0.45} />
              <stop offset="100%" stopColor="#4f9cff" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="#1c2740" vertical={false} />
          <XAxis
            dataKey="period"
            stroke="#5e6f8f"
            tick={{ fontSize: 12 }}
            tickLine={false}
            axisLine={{ stroke: "#1c2740" }}
          />
          <YAxis
            stroke="#5e6f8f"
            tick={{ fontSize: 12 }}
            tickLine={false}
            axisLine={false}
            tickFormatter={pct}
            domain={[0, "auto"]}
          />
          <Tooltip
            cursor={{ stroke: "#2a3a5c", strokeWidth: 1 }}
            contentStyle={{
              background: "#0d1422",
              border: "1px solid #2a3a5c",
              borderRadius: 10,
              color: "#e8eef9",
              fontSize: 12,
            }}
            labelStyle={{ color: "#9fb0cc" }}
            formatter={(value: number) => [pct(value), "Participation"]}
          />
          <Area
            type="monotone"
            dataKey="value"
            stroke="#4f9cff"
            strokeWidth={2}
            fill="url(#participationFill)"
            dot={{ r: 3, fill: "#4f9cff", strokeWidth: 0 }}
            activeDot={{ r: 5, fill: "#2dd4bf", strokeWidth: 0 }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
