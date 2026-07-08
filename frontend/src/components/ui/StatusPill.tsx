// frontend/src/components/ui/StatusPill.tsx
import type { ReactNode } from "react";

export type StatusKind = "ok" | "warn" | "crit";

const KIND_STYLES: Record<StatusKind, { pill: string; dot: string }> = {
  ok: { pill: "border-teal/30 bg-teal/10 text-teal", dot: "bg-teal" },
  warn: { pill: "border-amber/30 bg-amber/10 text-amber", dot: "bg-amber" },
  crit: {
    pill: "border-state-critical/30 bg-state-critical/10 text-state-critical",
    dot: "bg-state-critical",
  },
};

interface Props {
  kind: StatusKind;
  children: ReactNode;
}

/**
 * Semantic status pill — always pairs the color with a label (never
 * color-only), so meaning survives for colorblind users / grayscale prints.
 */
export function StatusPill({ kind, children }: Props) {
  const s = KIND_STYLES[kind];
  return (
    <span className={`pill ${s.pill}`}>
      <span className={`h-1.5 w-1.5 rounded-full ${s.dot}`} aria-hidden="true" />
      {children}
    </span>
  );
}
