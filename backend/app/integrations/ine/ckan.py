"""CKAN client for datos.gob.mx (the INE's open-data catalog).

Wraps the CKAN "action" API. All responses are JSON. No authentication needed
for public datasets.

Docs: https://docs.ckan.org/en/latest/api/
"""

from __future__ import annotations

from typing import Any

from app.integrations.ine import config
from app.integrations.ine.base import IneSourceError, build_client, get_bytes, get_json


def _action_url(action: str) -> str:
    return f"{config.CKAN_BASE_URL.rstrip('/')}/{action}"


def _unwrap(payload: dict[str, Any]) -> Any:
    """Validate a CKAN envelope and return its ``result``."""
    if not isinstance(payload, dict) or not payload.get("success", False):
        raise IneSourceError(f"CKAN returned an unsuccessful response: {payload!r:.200}")
    return payload.get("result")


def package_search(
    query: str = "",
    *,
    rows: int = 20,
    start: int = 0,
    fq: str | None = None,
) -> dict[str, Any]:
    """Search datasets. Returns ``{count, results: [...]}``."""
    params: dict[str, Any] = {"q": query, "rows": rows, "start": start}
    if fq:
        params["fq"] = fq
    return _unwrap(get_json(_action_url("package_search"), params=params))


def package_show(dataset_id: str) -> dict[str, Any]:
    """Fetch a single dataset (package) with its resources."""
    return _unwrap(get_json(_action_url("package_show"), params={"id": dataset_id}))


def organization_list() -> list[str]:
    """List organization slugs publishing data."""
    return _unwrap(get_json(_action_url("organization_list")))


def datastore_search(
    resource_id: str,
    *,
    query: str | None = None,
    limit: int = 100,
    offset: int = 0,
    filters: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Query a tabular resource via the CKAN DataStore (if enabled for it)."""
    params: dict[str, Any] = {"resource_id": resource_id, "limit": limit, "offset": offset}
    if query:
        params["q"] = query
    if filters:
        import json

        params["filters"] = json.dumps(filters)
    return _unwrap(get_json(_action_url("datastore_search"), params=params))


def search_ine_datasets(query: str = "", *, rows: int = 50) -> dict[str, Any]:
    """Search datasets published by the INE specifically."""
    # CKAN organization slugs vary; filter by INE in title/notes as a fallback.
    fq = 'organization:instituto-nacional-electoral OR title:INE OR notes:"INE"'
    return package_search(query, rows=rows, fq=fq)


def download_resource(resource_url: str) -> bytes:
    """Download a resource file (CSV, ZIP, shapefile, …) by its URL."""
    with build_client() as client:
        return get_bytes(resource_url, client=client)
