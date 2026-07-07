// frontend/src/components/charts/ChartFrame.tsx
import type { ReactNode } from "react";

export interface ChartFrameLegendItem { label: string; color: string; }

interface ChartFrameProps {
  title: string;
  caption?: string;
  legend?: ChartFrameLegendItem[];
  empty?: boolean;
  loading?: boolean;
  children: ReactNode;
}

/** Themed card wrapper shared by every Atenea chart: title/caption header,
 * empty/loading states, and an optional legend row. */
export function ChartFrame({ title, caption, legend, empty, loading, children }: ChartFrameProps) {
  return (
    <div className="card-premium reveal p-5">
      <div className="flex items-baseline justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold tracking-tight text-ink">{title}</h3>
          {caption && <p className="mt-0.5 text-xs text-ink-faint">{caption}</p>}
        </div>
      </div>
      <div className="mt-3">
        {loading ? (
          <div className="h-40 animate-pulse rounded-card bg-panel-hover" />
        ) : empty ? (
          <div className="flex h-40 items-center justify-center text-sm text-ink-faint">Sin datos para mostrar</div>
        ) : (
          children
        )}
      </div>
      {legend && legend.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-3 text-xs text-ink-muted">
          {legend.map((l) => (
            <span key={l.label} className="inline-flex items-center gap-1.5">
              <i className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: l.color }} />
              {l.label}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
