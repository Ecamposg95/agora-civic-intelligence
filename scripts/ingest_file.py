#!/usr/bin/env python
"""CLI to ingest a tabular or geo file into Ágora via the SP0b-1/2a ingestion engine.

Examples:
  # Ingest a census CSV as a global (org-less) source
  python scripts/ingest_file.py census --file data/censo2020.csv \\
      --source "INEGI 2020" --global --anio 2020

  # Ingest geometry from a GeoJSON file
  python scripts/ingest_file.py geometria --file data/distritos.geojson \\
      --source "INE 2021" --global --level distrito_federal \\
      --name-prop NOMBRE --code-prop CLAVE --replace
"""

from __future__ import annotations

import argparse
import os
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import select  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.ingestion.datasets import DATASETS  # noqa: E402
from app.ingestion.engine import IngestRunResult, run_ingest  # noqa: E402
from app.ingestion.resolve import ResolveResult, resolve_area_ids  # noqa: E402
from app.models.census import CensusMetric  # noqa: E402
from app.models.economic_unit import EconomicUnit  # noqa: E402
from app.models.election_result import ElectionResult  # noqa: E402
from app.models.electoral_area import AreaLevel  # noqa: E402
from app.models.socio import SocioMetric  # noqa: E402
from app.models.ingestion import DataSource, SourceKind  # noqa: E402
from app.models.organization import Organization  # noqa: E402


class _CliCtx:
    """Minimal context object accepted by run_ingest."""

    def __init__(self, org_id):
        self.organization_id = org_id
        self.campaign_id = None
        self.is_superadmin = True
        self.user = types.SimpleNamespace(id="cli")


def get_or_create_source(db, name: str, org_id) -> DataSource:
    """Return the DataSource with (organization_id, name), creating it if absent."""
    stmt = select(DataSource).where(DataSource.name == name)
    if org_id is None:
        stmt = stmt.where(DataSource.organization_id.is_(None))
    else:
        stmt = stmt.where(DataSource.organization_id == org_id)
    src = db.execute(stmt).scalar_one_or_none()
    if src is None:
        src = DataSource(name=name, organization_id=org_id, kind=SourceKind.FILE_CSV)
        db.add(src)
        db.flush()
    return src


def ingest(
    dataset: str,
    file: str,
    source: str,
    org,
    campaign,
    extra=None,
    replace: bool = False,
) -> IngestRunResult:
    """Core ingestion logic — importable and testable independently of argparse."""
    if dataset not in DATASETS:
        raise SystemExit(
            f"Unknown dataset '{dataset}'. Available: {sorted(DATASETS)}"
        )

    db = SessionLocal()
    try:
        # Resolve organisation
        org_id = None
        if org is not None:
            row = db.execute(
                select(Organization).where(Organization.slug == org)
            ).scalar_one_or_none()
            if row is None:
                raise SystemExit(
                    f"Organization with slug '{org}' not found. Seed it first."
                )
            org_id = row.id

        src = get_or_create_source(db, source, org_id)
        ctx = _CliCtx(org_id)

        res = run_ingest(
            db,
            ctx,
            DATASETS[dataset],
            file,
            source=src,
            extra=extra or {},
            replace=replace,
        )
        print(
            f"[ingest_file] dataset={dataset} status={res.status} "
            f"inserted={res.inserted} skipped={res.skipped}"
        )
        return res
    finally:
        db.close()


_CENSUS_LEVEL_MAP = {
    "estado": AreaLevel.ESTADO,
    "municipio": AreaLevel.MUNICIPIO,
}

_FACT_LEVEL_MAP = {
    "estado": AreaLevel.ESTADO,
    "municipio": AreaLevel.MUNICIPIO,
    "seccion": AreaLevel.SECCION,
}

_RESOLVE_DATASETS = {
    "census": (CensusMetric, _CENSUS_LEVEL_MAP),
    "resultados": (ElectionResult, _FACT_LEVEL_MAP),
    "socio": (SocioMetric, _FACT_LEVEL_MAP),
    "denue": (EconomicUnit, _FACT_LEVEL_MAP),
}


def resolve(dataset: str) -> ResolveResult:
    """Resolve area_id for all NULL-area_id rows of *dataset*. Importable."""
    if dataset not in _RESOLVE_DATASETS:
        raise SystemExit(
            f"Unknown resolve dataset '{dataset}'. Available: {sorted(_RESOLVE_DATASETS)}"
        )
    fact_model, level_map = _RESOLVE_DATASETS[dataset]
    db = SessionLocal()
    try:
        result = resolve_area_ids(db, fact_model, level_map)
        print(
            f"[ingest_file resolve] dataset={dataset} matched={result.matched} unmatched={result.unmatched}"
        )
        return result
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ingest a tabular or geo file into Ágora via the SP0b engine"
    )
    subparsers = parser.add_subparsers(dest="dataset", required=True)

    # ── census subcommand ─────────────────────────────────────────────────────
    census_p = subparsers.add_parser("census", help="Ingest a census tabular CSV")
    census_p.add_argument("--file", required=True, help="Path to the input file")
    census_p.add_argument("--source", required=True, help="Human-readable data source name")
    census_scope = census_p.add_mutually_exclusive_group()
    census_scope.add_argument(
        "--global", dest="global_scope", action="store_true", default=True,
        help="Ingest as a global (org-less) source (default)",
    )
    census_scope.add_argument(
        "--org", dest="org", metavar="SLUG", default=None,
        help="Scope to organisation by slug",
    )
    census_p.add_argument("--campaign", dest="campaign", metavar="ID", default=None)
    census_p.add_argument("--anio", type=int, default=None, help="Year (required for census)")
    census_p.add_argument("--replace", action="store_true",
                          help="Delete prior rows matching this scope before inserting")

    # ── geometria subcommand ──────────────────────────────────────────────────
    geo_p = subparsers.add_parser("geometria", help="Ingest geometry from GeoJSON or Shapefile")
    geo_p.add_argument("--file", required=True, help="Path to the GeoJSON / SHP file")
    geo_p.add_argument("--source", required=True, help="Human-readable data source name")
    geo_scope = geo_p.add_mutually_exclusive_group()
    geo_scope.add_argument(
        "--global", dest="global_scope", action="store_true", default=True,
        help="Ingest as global reference cartography (default)",
    )
    geo_scope.add_argument(
        "--org", dest="org", metavar="SLUG", default=None,
        help="Scope to organisation by slug",
    )
    geo_p.add_argument("--level", required=True,
                       help="AreaLevel value (e.g. distrito_federal, municipio, seccion)")
    geo_p.add_argument("--name-prop", dest="name_prop", default="name",
                       help="Feature property holding the area name (default: name)")
    geo_p.add_argument("--code-prop", dest="code_prop", default="code",
                       help="Feature property holding the area code (default: code)")
    geo_p.add_argument("--parent-prop", dest="parent_prop", default=None,
                       help="Feature property holding the parent code (optional)")
    geo_p.add_argument("--replace", action="store_true",
                       help="Delete prior rows for this level before inserting")

    # ── resultados ────────────────────────────────────────────────────────────
    res_p = subparsers.add_parser("resultados", help="Ingest election results CSV")
    res_p.add_argument("--file", required=True)
    res_p.add_argument("--source", required=True)
    res_p.add_argument("--org", dest="org", default=None)
    res_p.add_argument("--anio", type=int, required=True)
    res_p.add_argument("--eleccion", required=True,
                       help="Election identity, e.g. presidencia / diputaciones_federales")
    res_p.add_argument("--nivel", default=None, help="Optional nivel for --replace scope")
    res_p.add_argument("--replace", action="store_true")

    # ── socio ─────────────────────────────────────────────────────────────────
    soc_p = subparsers.add_parser("socio", help="Ingest socioeconomic metrics CSV")
    soc_p.add_argument("--file", required=True)
    soc_p.add_argument("--source", required=True)
    soc_p.add_argument("--org", dest="org", default=None)
    soc_p.add_argument("--anio", type=int, required=True)
    soc_p.add_argument("--nivel", default=None)
    soc_p.add_argument("--replace", action="store_true")

    # ── denue ─────────────────────────────────────────────────────────────────
    den_p = subparsers.add_parser("denue", help="Ingest DENUE economic units CSV (lat/lon)")
    den_p.add_argument("--file", required=True)
    den_p.add_argument("--source", required=True)
    den_p.add_argument("--org", dest="org", default=None)
    den_p.add_argument("--replace", action="store_true")

    # ── casillas ──────────────────────────────────────────────────────────────
    cas_p = subparsers.add_parser("casillas", help="Ingest casilla points as electoral_areas")
    cas_p.add_argument("--file", required=True)
    cas_p.add_argument("--source", required=True)
    cas_p.add_argument("--replace", action="store_true")

    # ── resolve subcommand ────────────────────────────────────────────────────
    resolve_p = subparsers.add_parser(
        "resolve",
        help="Resolve area_id for NULL-area_id rows by matching territory_code -> electoral_areas.code",
    )
    resolve_p.add_argument(
        "--dataset",
        dest="resolve_dataset",
        required=True,
        choices=sorted(_RESOLVE_DATASETS),
        help="Which fact table to resolve (e.g. census)",
    )

    args = parser.parse_args()

    if args.dataset == "resolve":
        resolve(args.resolve_dataset)
    elif args.dataset == "census":
        ingest(
            dataset="census",
            file=args.file,
            source=args.source,
            org=args.org,
            campaign=args.campaign,
            extra={"anio": args.anio},
            replace=args.replace,
        )
    elif args.dataset == "geometria":
        ingest(
            dataset="geometria",
            file=args.file,
            source=args.source,
            org=args.org,
            campaign=None,
            extra={
                "level": args.level,
                "name_prop": args.name_prop,
                "code_prop": args.code_prop,
                "parent_prop": args.parent_prop,
            },
            replace=args.replace,
        )
    elif args.dataset == "resultados":
        ingest(dataset="resultados", file=args.file, source=args.source, org=args.org,
               campaign=None, extra={"anio": args.anio, "eleccion": args.eleccion,
                                     "nivel": args.nivel}, replace=args.replace)
    elif args.dataset == "socio":
        ingest(dataset="socio", file=args.file, source=args.source, org=args.org,
               campaign=None, extra={"anio": args.anio, "nivel": args.nivel},
               replace=args.replace)
    elif args.dataset == "denue":
        ingest(dataset="denue", file=args.file, source=args.source, org=args.org,
               campaign=None, extra={}, replace=args.replace)
    elif args.dataset == "casillas":
        ingest(dataset="casillas", file=args.file, source=args.source, org=None,
               campaign=None, extra={}, replace=args.replace)


if __name__ == "__main__":
    main()
