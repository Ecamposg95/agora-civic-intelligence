import { useEffect, useMemo, useState } from "react";

import { getAreas, getLayers } from "@/api/maps";
import { getWmsLayers } from "@/api/sources";
import { AppLayout } from "@/components/layout/AppLayout";
import { LayerPanel } from "@/components/maps/LayerPanel";
import { MapCanvas, type WmsOverlay } from "@/components/maps/MapCanvas";
import type { AreasResponse, MapLayer } from "@/types/maps";

export function MapExplorerPage() {
  const [layers, setLayers] = useState<MapLayer[]>([]);
  const [areas, setAreas] = useState<AreasResponse | null>(null);
  // Tile templates for WMS layers, keyed by their synthetic "wms:<id>" id.
  const [wmsTiles, setWmsTiles] = useState<Record<string, string[]>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.allSettled([getLayers(), getAreas(), getWmsLayers()])
      .then(([layersRes, areasRes, wmsRes]) => {
        const base: MapLayer[] =
          layersRes.status === "fulfilled" ? layersRes.value.layers : [];
        if (layersRes.status === "rejected") {
          setError(layersRes.reason?.message ?? "Failed to load layers");
        }

        // Merge INE SIGE WMS layers as toggleable territorial raster layers.
        const tiles: Record<string, string[]> = {};
        const wmsLayers: MapLayer[] =
          wmsRes.status === "fulfilled"
            ? wmsRes.value.layers.map((w) => {
                const id = `wms:${w.id}`;
                tiles[id] = w.tiles;
                return {
                  id,
                  name: `${w.name} (INE)`,
                  category: "territorial",
                  geometry_type: "raster",
                  srid: w.srid,
                  visible: false,
                  description: `WMS · ${w.level}`,
                } as MapLayer;
              })
            : [];
        setWmsTiles(tiles);
        setLayers([...base, ...wmsLayers]);

        setAreas(
          areasRes.status === "fulfilled"
            ? areasRes.value
            : { type: "FeatureCollection", features: [] },
        );
      })
      .finally(() => setLoading(false));
  }, []);

  const toggle = (id: string) =>
    setLayers((prev) =>
      prev.map((l) => (l.id === id ? { ...l, visible: !l.visible } : l)),
    );

  // Areas overlay follows the electoral districts catalog layer (default on).
  const showAreas = useMemo(() => {
    const districts = layers.find((l) => l.id === "electoral_districts");
    return districts ? districts.visible : true;
  }, [layers]);

  const wmsOverlays: WmsOverlay[] = useMemo(
    () =>
      layers
        .filter((l) => l.id.startsWith("wms:") && wmsTiles[l.id])
        .map((l) => ({ id: l.id, tiles: wmsTiles[l.id], visible: l.visible })),
    [layers, wmsTiles],
  );

  return (
    <AppLayout title="Map Explorer" crumb="Electoral & Territorial Layers">
      <div className="mb-6">
        <div className="eyebrow">Geospatial intelligence</div>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight text-ink">
          Map Explorer
        </h1>
        <p className="mt-1 max-w-xl text-sm text-ink-muted">
          Explora distritos, secciones y superficies analíticas. Activa capas
          gobernadas (incluyendo WMS del SIGE/INE) sobre el basemap institucional.
        </p>
      </div>

      {error && (
        <div className="mb-4 rounded-lg border border-state-critical/40 bg-state-critical/10 px-3 py-2 text-sm text-state-critical">
          {error}
        </div>
      )}

      <div className="grid h-[calc(100vh-15rem)] grid-cols-1 gap-4 lg:grid-cols-[320px_1fr]">
        <LayerPanel layers={layers} onToggle={toggle} loading={loading} />
        <MapCanvas areas={areas} showAreas={showAreas} wmsLayers={wmsOverlays} />
      </div>
    </AppLayout>
  );
}
