"""CLI: importar promovidos desde XLSX a Registro. Uso:

  python3 scripts/import_promovidos.py --campaign <campaign_id> --dir docs/data/separados [--dry-run]

Nunca imprime PII (solo conteos por archivo).
"""
import argparse
import glob
import os
import sys

from sqlalchemy import select

from app.database import SessionLocal
from app.models.campaign import Campaign
from app.services import import_service


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--campaign", required=True)
    ap.add_argument("--dir", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    db = SessionLocal()
    try:
        camp = db.execute(select(Campaign).where(Campaign.id == args.campaign)).scalar_one_or_none()
        if camp is None:
            print(f"campaign {args.campaign} not found", file=sys.stderr)
            return 2
        org_id = camp.organization_id
        files = sorted(glob.glob(os.path.join(args.dir, "*.xlsx")))
        total = {"leidas": 0, "importadas": 0, "duplicadas": 0}
        for i, f in enumerate(files, 1):
            if args.dry_run:
                rows = import_service.parse_workbook(f)
                print(f"[{i}/{len(files)}] {len(rows)} filas (dry-run)")
                continue
            res = import_service.import_rows(
                db, organization_id=org_id, campaign_id=args.campaign, path=f)
            for k in total:
                total[k] += res[k]
            print(f"[{i}/{len(files)}] {res}")
        print(f"TOTAL: {total}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
