"""SIGE / Marco Geográfico Electoral — cartography access.

Two consumption modes:
  1. WMS layer descriptors for the frontend map (MapLibre raster source), built
     from the configured ``INE_SIGE_WMS_URL``.
  2. Direct GeoJSON fetch for ingestion into PostGIS (any GeoJSON URL).

Full vector products (Shapefile/GeoJSON) may require an INE access request; the
WMS overlay needs only the service URL.
"""

from __future__ import annotations

from typing import Any

from app.integrations.ine import config
from app.integrations.ine.base import build_client, get_bytes, get_json

# Canonical Marco Geográfico Electoral layers (WMS layer names are placeholders
# until confirmed against the live GetCapabilities).
CARTOGRAPHY_LAYERS = [
    {"id": "entidades", "name": "Entidades federativas", "level": "entidad"},
    {"id": "distritos_federales", "name": "Distritos federales", "level": "distrito_federal"},
    {"id": "distritos_locales", "name": "Distritos locales", "level": "distrito_local"},
    {"id": "municipios", "name": "Municipios", "level": "municipio"},
    {"id": "secciones", "name": "Secciones electorales", "level": "seccion"},
]


def wms_configured() -> bool:
    """True when a WMS endpoint has been configured."""
    return bool(config.SIGE_WMS_URL)


def wms_layers() -> list[dict[str, Any]]:
    """Return MapLibre-ready WMS raster source descriptors.

    Empty when ``INE_SIGE_WMS_URL`` is unset (the frontend then shows the
    basemap only).
    """
    if not wms_configured():
        return []
    base = config.SIGE_WMS_URL.rstrip("/")
    descriptors: list[dict[str, Any]] = []
    for layer in CARTOGRAPHY_LAYERS:
        tile_url = (
            f"{base}?service=WMS&version=1.1.1&request=GetMap"
            f"&layers={layer['id']}&styles=&format=image/png&transparent=true"
            "&srs=EPSG:3857&bbox={bbox-epsg-3857}&width=256&height=256"
        )
        descriptors.append(
            {
                "id": layer["id"],
                "name": layer["name"],
                "level": layer["level"],
                "type": "raster",
                "tiles": [tile_url],
                "tileSize": 256,
                "srid": 4326,
            }
        )
    return descriptors


def fetch_geojson(url: str) -> dict[str, Any]:
    """Fetch a GeoJSON FeatureCollection from a URL (for ingestion)."""
    with build_client() as client:
        return get_json(url, client=client)


def download(url: str) -> bytes:
    """Download a raw cartographic file (Shapefile ZIP, etc.)."""
    with build_client() as client:
        return get_bytes(url, client=client)
