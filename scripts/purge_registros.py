#!/usr/bin/env python
"""CLI to run the Ágora data-retention purge (AC-7.4).

Purges expired registros in two passes:
  Pass A — soft-deleted rows older than RETENTION_PURGE_SOFT_DELETED_DAYS (default 30).
  Pass B — all rows for campaigns whose max(election_date) +
            RETENTION_DAYS_AFTER_ELECTION days (default 180) has passed.

Run as a Railway one-off or cron job — NOT in the app lifespan.

Examples
--------
  # Preview what would be deleted (no changes written):
  python scripts/purge_registros.py --dry-run

  # Actually purge (RETENTION_ENABLED env var must be "true"):
  RETENTION_ENABLED=true python scripts/purge_registros.py --apply

Railway cron example (railway.toml):
  [cron.retention]
  schedule = "0 3 * * 0"          # weekly, Sunday 03:00 UTC
  command   = "python scripts/purge_registros.py --apply"

Required environment variables
-------------------------------
  DATABASE_URL                         — PostgreSQL connection URL
  RETENTION_ENABLED=true               — gate; defaults to False (no-op)
  FERNET_KEY                           — required by app startup
  RETENTION_DAYS_AFTER_ELECTION        — optional; default 180
  RETENTION_PURGE_SOFT_DELETED_DAYS    — optional; default 30
"""

from __future__ import annotations

import argparse
import os
import sys

# Allow running from the repo root OR from the scripts/ directory.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.database import SessionLocal  # noqa: E402
from app.services.retention_service import purge_expired  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ágora data-retention purge (AC-7.4)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "RETENTION_ENABLED=true must be set in the environment for --apply to delete data.\n"
            "Without it the service returns a no-op regardless of the flag."
        ),
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Report eligible counts without deleting anything",
    )
    mode.add_argument(
        "--apply",
        action="store_true",
        help="Permanently purge eligible registros (requires RETENTION_ENABLED=true)",
    )
    args = parser.parse_args()

    dry_run: bool = args.dry_run
    db = SessionLocal()
    try:
        result = purge_expired(db, dry_run=dry_run)

        prefix = "[DRY-RUN] " if dry_run else ""

        if result.total_purged == 0:
            print(f"{prefix}[purge_registros] No eligible records found — nothing to purge.")
        else:
            print(
                f"{prefix}[purge_registros] "
                f"soft_deleted_purged={result.soft_deleted_purged} "
                f"post_election_purged={result.post_election_purged} "
                f"campaigns_purged={result.campaigns_purged} "
                f"total={result.total_purged}"
            )

        # Warn if RETENTION_ENABLED is off (applies to --apply too)
        from app.core.config import settings
        if not dry_run and not settings.RETENTION_ENABLED:
            print(
                "[purge_registros] WARNING: RETENTION_ENABLED=False — "
                "no data was purged.  Set RETENTION_ENABLED=true to enable."
            )
    finally:
        db.close()


if __name__ == "__main__":
    main()
