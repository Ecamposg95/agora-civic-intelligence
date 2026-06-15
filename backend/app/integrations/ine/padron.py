"""Padrón Electoral / Lista Nominal statistics via the CKAN catalog.

These aggregate statistics (by age range, state and sex) are published as
datasets on datos.gob.mx, so this module is a thin convenience layer over the
CKAN client.
"""

from __future__ import annotations

from typing import Any

from app.integrations.ine import ckan


def search_padron_datasets(rows: int = 50) -> dict[str, Any]:
    """Find Padrón Electoral / Lista Nominal datasets."""
    return ckan.search_ine_datasets("padrón electoral lista nominal", rows=rows)


def latest_lista_nominal_resources() -> list[dict[str, Any]]:
    """Return downloadable resources from the most relevant Lista Nominal dataset."""
    found = search_padron_datasets(rows=10)
    results = found.get("results", []) if isinstance(found, dict) else []
    resources: list[dict[str, Any]] = []
    for dataset in results:
        for resource in dataset.get("resources", []):
            resources.append(
                {
                    "dataset": dataset.get("title"),
                    "name": resource.get("name"),
                    "format": resource.get("format"),
                    "url": resource.get("url"),
                }
            )
    return resources
