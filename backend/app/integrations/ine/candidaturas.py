"""Client for the Candidaturas MX open API (apielectoral.mx).

A SocialTIC project following the Popolo standard. JSON/REST, no auth, free.
Exact resource paths come from the project's documentation; they are kept as
overridable constants so they can be corrected without touching call sites.
"""

from __future__ import annotations

import os
from typing import Any

from app.integrations.ine import config
from app.integrations.ine.base import get_json

# Popolo-style collections. Override via env if the published paths differ.
PATH_PERSONS = os.getenv("INE_CANDIDATURAS_PERSONS", "/personas")
PATH_ORGANIZATIONS = os.getenv("INE_CANDIDATURAS_ORGS", "/organizaciones")
PATH_AREAS = os.getenv("INE_CANDIDATURAS_AREAS", "/areas")
PATH_POSTS = os.getenv("INE_CANDIDATURAS_POSTS", "/cargos")


def _url(path: str) -> str:
    return f"{config.CANDIDATURAS_BASE_URL.rstrip('/')}/{path.lstrip('/')}"


def get(path: str, params: dict[str, Any] | None = None) -> Any:
    """Generic GET against the Candidaturas MX API."""
    return get_json(_url(path), params=params)


def list_persons(params: dict[str, Any] | None = None) -> Any:
    """Candidate profiles (Popolo ``persons``)."""
    return get(PATH_PERSONS, params=params)


def list_organizations(params: dict[str, Any] | None = None) -> Any:
    """Parties / organizations (Popolo ``organizations``)."""
    return get(PATH_ORGANIZATIONS, params=params)


def list_areas(params: dict[str, Any] | None = None) -> Any:
    """Electoral geography (Popolo ``areas``): districts, states, municipalities."""
    return get(PATH_AREAS, params=params)


def list_posts(params: dict[str, Any] | None = None) -> Any:
    """Contested posts / offices (Popolo ``posts``)."""
    return get(PATH_POSTS, params=params)
