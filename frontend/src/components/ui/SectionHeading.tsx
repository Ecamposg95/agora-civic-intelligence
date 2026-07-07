interface SectionHeadingProps {
  eyebrow?: string;
  title: string;
  note?: string;
}

/**
 * Section heading with coral accent dot, uppercase title, and optional note.
 * Used as a divider/separator between major content blocks.
 *
 * @example
 * <SectionHeading title="Casos" note="hoy" />
 */
export function SectionHeading({
  eyebrow,
  title,
  note,
}: SectionHeadingProps) {
  return (
    <div className="flex items-center justify-between gap-4">
      {/* Left section with accent dot, eyebrow, and title */}
      <div className="flex items-center gap-2.5">
        {/* Coral accent dot using --c-warm */}
        <div className="h-2 w-2 rounded-full bg-warm" />
        <div>
          {eyebrow && <div className="eyebrow">{eyebrow}</div>}
          <h2 className="font-display text-lg font-bold uppercase tracking-widest text-ink">
            {title}
          </h2>
        </div>
      </div>
      {/* Right section with optional note */}
      {note && (
        <div className="text-right text-sm text-ink-muted">{note}</div>
      )}
    </div>
  );
}
