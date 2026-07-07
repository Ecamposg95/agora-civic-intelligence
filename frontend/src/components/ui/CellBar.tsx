// frontend/src/components/ui/CellBar.tsx

interface Props {
  /** Coverage/progress value in the 0..100 range; out-of-range values are clamped. */
  value: number;
}

/** Mini coverage bar + percentage label, for dense table cells. Teal fill. */
export function CellBar({ value }: Props) {
  const clamped = Math.max(0, Math.min(100, Math.round(value)));

  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-16 shrink-0 overflow-hidden rounded-full bg-line/60">
        <div
          className="h-full rounded-full bg-teal"
          style={{ width: `${clamped}%` }}
          role="progressbar"
          aria-valuenow={clamped}
          aria-valuemin={0}
          aria-valuemax={100}
        />
      </div>
      <span className="font-mono text-xs tabular-nums text-ink-muted">{clamped}%</span>
    </div>
  );
}
