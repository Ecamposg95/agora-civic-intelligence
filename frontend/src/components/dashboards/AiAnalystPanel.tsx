import { AiIcon } from "@/components/ui/icons";

/** Placeholder for the Institutional AI Analyst. Model wiring comes later. */
export function AiAnalystPanel() {
  return (
    <div className="panel-raised overflow-hidden p-5">
      <span className="pill border-accent/30 bg-accent/10 text-accent">
        <AiIcon width={14} height={14} /> Institutional AI Analyst
      </span>
      <div className="mt-4 rounded-lg border border-line bg-bg-sunken p-4 text-sm leading-relaxed text-ink-muted">
        Ask about participation trends, electoral coverage, or territorial
        anomalies. The AI analyst synthesizes governed civic data into
        executive-grade briefings — with full source traceability and audit
        logging.
      </div>
      <div className="mt-4 flex gap-2">
        <input
          className="field-input flex-1"
          placeholder="e.g. Summarize participation shifts in District 12…"
          disabled
        />
        <button className="btn-primary" disabled>
          Analyze
        </button>
      </div>
      <p className="mt-3 text-[11px] text-ink-faint">
        Preview — connect a model provider later.
      </p>
    </div>
  );
}
