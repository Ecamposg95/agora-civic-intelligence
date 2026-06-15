"""Unit tests for INE integrations (no network).

Cover the pure logic: level mapping, PREP CSV parsing, CKAN envelope handling,
and the source registry shape.
"""

import pytest

from app.integrations.ine import config, prep
from app.integrations.ine.base import IneSourceError
from app.integrations.ine.ckan import _unwrap
from app.models.electoral_area import AreaLevel


def test_level_mapping_known_and_default() -> None:
    assert config.map_level("seccion") == AreaLevel.PRECINCT
    assert config.map_level("ENTIDAD") == AreaLevel.STATE
    assert config.map_level("distrito_local") == AreaLevel.DISTRICT
    assert config.map_level("municipio") == AreaLevel.MUNICIPALITY
    # Unknown / empty fall back to DISTRICT.
    assert config.map_level("desconocido") == AreaLevel.DISTRICT
    assert config.map_level(None) == AreaLevel.DISTRICT


def test_source_registry_is_well_formed() -> None:
    ids = {s.id for s in config.SOURCES}
    assert {"datos_gob_ckan", "candidaturas_mx", "sige_cartografia", "prep"} <= ids
    for s in config.SOURCES:
        assert s.kind in {"api", "wms", "download", "portal"}
        assert s.base_url
        assert isinstance(s.formats, list)


def test_prep_csv_parse_skips_metadata() -> None:
    sample = "\n".join(
        [
            "PREP 2024 | Generado: 2024-06-02",  # metadata line (few fields)
            "ID_ESTADO|ESTADO|ID_DISTRITO|DISTRITO|TOTAL_VOTOS|LISTA_NOMINAL",
            "9|CIUDAD DE MEXICO|1|01 GAM|1234|5000",
            "9|CIUDAD DE MEXICO|2|02 AO|2345|6000",
        ]
    )
    rows = prep.parse_csv(sample)
    assert len(rows) == 2
    assert rows[0]["ESTADO"] == "CIUDAD DE MEXICO"
    assert rows[0]["TOTAL_VOTOS"] == "1234"
    assert rows[1]["ID_DISTRITO"] == "2"


def test_prep_csv_parse_empty() -> None:
    assert prep.parse_csv("") == []


def test_ckan_unwrap_success_and_failure() -> None:
    assert _unwrap({"success": True, "result": {"count": 0}}) == {"count": 0}
    with pytest.raises(IneSourceError):
        _unwrap({"success": False, "error": "boom"})
