import type { ReactNode } from "react";
import { ArrowUpIcon } from "./icons";

interface MetricCardProps {
  label: string;
  value: string;
  delta?: string;
  icon?: ReactNode;
}

export function MetricCard({ label, value, delta, icon }: MetricCardProps) {
  return (
    <div className="panel p-5">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-wide text-ink-muted">
          {label}
        </span>
        {icon && <span className="text-accent">{icon}</span>}
      </div>
      <div className="mt-3 text-3xl font-semibold tracking-tight text-ink">
        {value}
      </div>
      {delta ? (
        <span className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-teal">
          <ArrowUpIcon /> {delta}
        </span>
      ) : (
        <span className="mt-2 inline-flex text-xs text-ink-faint">Baseline</span>
      )}
    </div>
  );
}
