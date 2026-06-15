import type { LayerCategory, MapLayer } from "@/types/maps";

interface LayerPanelProps {
  layers: MapLayer[];
  onToggle: (id: string) => void;
  loading?: boolean;
}

const CATEGORY_TAG: Record<LayerCategory, string> = {
  electoral: "border-accent/30 bg-accent/10 text-accent",
  analytics: "border-teal/30 bg-teal/10 text-teal",
  territorial: "border-state-warning/30 bg-state-warning/10 text-state-warning",
};

export function LayerPanel({ layers, onToggle, loading }: LayerPanelProps) {
  if (loading) {
    return (
      <div className="panel h-full p-5">
        <div className="mb-4 text-sm font-semibold text-ink">Data Layers</div>
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="mb-2 h-14 animate-pulse rounded-lg bg-panel-hover"
          />
        ))}
      </div>
    );
  }

  const active = layers.filter((l) => l.visible).length;

  return (
    <div className="panel flex h-full flex-col overflow-y-auto p-5">
      <div className="mb-4 flex items-center justify-between">
        <span className="text-sm font-semibold text-ink">Data Layers</span>
        <span className="text-[11px] text-ink-faint">
          {active}/{layers.length} active
        </span>
      </div>

      {layers.length === 0 && (
        <p className="text-sm text-ink-faint">
          No layers available. Showing the basemap only.
        </p>
      )}

      <div className="flex flex-col gap-2">
        {layers.map((layer) => (
          <div
            key={layer.id}
            className="flex items-center justify-between rounded-lg border border-line bg-bg-sunken px-3 py-2.5"
          >
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="truncate text-sm text-ink">{layer.name}</span>
                <span className={`pill ${CATEGORY_TAG[layer.category]}`}>
                  {layer.category}
                </span>
              </div>
              <span className="text-[11px] text-ink-faint">
                {layer.geometry_type} · SRID {layer.srid}
              </span>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={layer.visible}
              aria-label={`Toggle ${layer.name}`}
              onClick={() => onToggle(layer.id)}
              className={`relative h-5 w-9 shrink-0 rounded-pill transition-colors ${
                layer.visible ? "bg-accent" : "bg-line-strong"
              }`}
            >
              <span
                className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-transform ${
                  layer.visible ? "translate-x-4" : "translate-x-0.5"
                }`}
              />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
