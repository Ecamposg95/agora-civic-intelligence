// frontend/src/components/charts/AreaTrend.tsx
import { useId } from "react";

export interface TrendPoint { x: string; y: number; }

interface AreaTrendProps {
  points: TrendPoint[];
  /** Line/area color; defaults to the first series token. */
  color?: string;
}

const WIDTH = 560;
const HEIGHT = 200;
const PAD_LEFT = 12;
const PAD_RIGHT = 12;
const PAD_TOP = 16;
const PAD_BOTTOM = 26;

const numberFormat = new Intl.NumberFormat("es-MX");

/** Series with a gradient-filled area, a 2.5px line, and an emphasized
 * endpoint (last value called out with a circle + label). */
export function AreaTrend({ points, color = "var(--chart-1)" }: AreaTrendProps) {
  const rawId = useId();
  const gradientId = `area-trend-gradient-${rawId.replace(/[^a-zA-Z0-9]/g, "")}`;

  const chartWidth = WIDTH - PAD_LEFT - PAD_RIGHT;
  const chartHeight = HEIGHT - PAD_TOP - PAD_BOTTOM;
  const baselineY = PAD_TOP + chartHeight;
  const maxY = Math.max(1, ...points.map((p) => p.y));

  const coords = points.map((p, i) => {
    const px = points.length > 1 ? PAD_LEFT + (i / (points.length - 1)) * chartWidth : PAD_LEFT + chartWidth / 2;
    const py = baselineY - (p.y / maxY) * chartHeight;
    return { px, py, label: p.x, value: p.y };
  });

  const linePath = coords.map((c, i) => `${i === 0 ? "M" : "L"}${c.px},${c.py}`).join(" ");
  const areaPath = coords.length
    ? `${linePath} L${coords[coords.length - 1].px},${baselineY} L${coords[0].px},${baselineY} Z`
    : "";

  const last = coords[coords.length - 1];
  const lastValueLabel = last ? numberFormat.format(last.value) : "0";
  const gridLines = [0, 0.5, 1].map((f) => PAD_TOP + chartHeight * f);

  return (
    <svg
      viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      role="img"
      aria-label={`Tendencia, último valor: ${lastValueLabel}`}
      className="w-full"
    >
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity={0.26} />
          <stop offset="100%" stopColor={color} stopOpacity={0} />
        </linearGradient>
      </defs>

      {gridLines.map((y, i) => (
        <line
          key={i}
          x1={PAD_LEFT}
          x2={WIDTH - PAD_RIGHT}
          y1={y}
          y2={y}
          stroke="var(--chart-grid)"
          strokeWidth={1}
        />
      ))}

      {areaPath && <path d={areaPath} fill={`url(#${gradientId})`} stroke="none" />}
      {linePath && (
        <path d={linePath} fill="none" stroke={color} strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" />
      )}

      {last && (
        <>
          <circle cx={last.px} cy={last.py} r={5} fill={color} stroke="rgb(var(--c-panel))" strokeWidth={2} />
          <text
            x={last.px}
            y={Math.max(last.py - 12, 10)}
            textAnchor="middle"
            fontSize={12}
            fontWeight={700}
            fill={color}
            style={{ fontVariantNumeric: "tabular-nums" }}
          >
            {lastValueLabel}
          </text>
        </>
      )}

      {coords.map((c, i) => (
        <text key={i} x={c.px} y={HEIGHT - 8} textAnchor="middle" fontSize={10} fill="var(--chart-axis)">
          {c.label}
        </text>
      ))}
    </svg>
  );
}
