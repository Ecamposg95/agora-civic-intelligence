import type { ReactNode } from "react";

interface PageHeaderProps {
  /** Small uppercase, tracked label above the title. */
  eyebrow?: string;
  /** Main title. Rendered with the display font, large and bold. */
  title: string;
  /**
   * Optional accent word(s) appended after the title and rendered with the
   * gradient treatment (e.g. title="Explorador" accent="Territorial").
   */
  accent?: string;
  /** Supporting copy below the title. */
  subtitle?: string;
  /** Right-aligned slot (buttons, links, stat chips). */
  actions?: ReactNode;
  /** Optional content below the header (e.g. a stats row). */
  children?: ReactNode;
}

/**
 * Premium "Command Center" page header. Mirrors the hero treatment of the
 * Dashboard and Map Explorer: soft auras behind a revealed block with an
 * eyebrow, a gradient-accented display title, an optional subtitle and a
 * right-aligned actions slot.
 */
export function PageHeader({
  eyebrow,
  title,
  accent,
  subtitle,
  actions,
  children,
}: PageHeaderProps) {
  return (
    <section className="relative mb-6 overflow-hidden">
      <div className="aura -left-16 -top-24 h-72 w-72" aria-hidden="true" />
      <div className="aura aura-teal right-0 -top-16 h-64 w-64" aria-hidden="true" />

      <div className="reveal relative flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
        <div className="min-w-0">
          {eyebrow && <div className="eyebrow">{eyebrow}</div>}
          <h1 className="mt-2 font-display text-3xl font-bold leading-[1.05] tracking-tight text-ink md:text-4xl">
            <span className="text-ink">{title}</span>
            {accent && (
              <>
                {" "}
                <span className="text-gradient">{accent}</span>
              </>
            )}
          </h1>
          {subtitle && (
            <p className="mt-3 max-w-xl text-sm leading-relaxed text-ink-muted">
              {subtitle}
            </p>
          )}
        </div>

        {actions && (
          <div
            className="reveal flex shrink-0 flex-wrap items-end gap-3"
            style={{ animationDelay: "80ms" }}
          >
            {actions}
          </div>
        )}
      </div>

      {children && (
        <div className="reveal relative mt-5" style={{ animationDelay: "120ms" }}>
          {children}
        </div>
      )}
    </section>
  );
}
