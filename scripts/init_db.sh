#!/usr/bin/env bash
# Initialize the database: enable PostGIS, create tables, seed base data.
# Thin wrapper around the idempotent bootstrap used on Railway.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "▶ Running idempotent bootstrap (PostGIS + tables + seed)…"
python scripts/railway_init.py

echo "✓ Database ready."
