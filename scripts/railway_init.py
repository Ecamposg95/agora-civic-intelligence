#!/usr/bin/env python
"""Manual database bootstrap entrypoint (local / CI / one-off).

The deployed app runs the same bootstrap automatically at startup via the
FastAPI lifespan (see ``backend/app/bootstrap.py``); it is intentionally NOT
wired to the Railway ``release`` phase, where private networking — and thus the
``*.railway.internal`` database host — does not resolve.

Seed credentials come from env (never hardcoded):
  SEED_ORG_NAME, SEED_ORG_SLUG, SEED_ADMIN_EMAIL, SEED_ADMIN_PASSWORD
"""

import os
import sys

# Allow running as `python scripts/railway_init.py` from the repo root.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.bootstrap import run_bootstrap  # noqa: E402


if __name__ == "__main__":
    run_bootstrap()
