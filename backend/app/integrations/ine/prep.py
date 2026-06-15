"""PREP / Cómputos results — downloader and parser.

The INE publishes results as a ZIP containing a pipe-delimited (``|``) CSV. The
file is preceded by metadata lines before the real header row, so the parser
detects the header heuristically (the first line with many delimiters).
"""

from __future__ import annotations

import csv
import io
import zipfile
from typing import Any

from app.integrations.ine.base import IneSourceError, build_client, get_bytes

DELIMITER = "|"
_MIN_HEADER_FIELDS = 5


def download_zip(url: str) -> bytes:
    """Download the PREP/Cómputos ZIP archive."""
    with build_client() as client:
        return get_bytes(url, client=client)


def extract_csv_text(zip_bytes: bytes, member: str | None = None) -> str:
    """Extract a CSV member from the ZIP as text.

    If ``member`` is omitted, the first ``.csv`` entry is used.
    """
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = zf.namelist()
        target = member or next((n for n in names if n.lower().endswith(".csv")), None)
        if target is None:
            raise IneSourceError(f"No CSV found in archive (members: {names})")
        return zf.read(target).decode("utf-8", errors="replace")


def _find_header_index(lines: list[str]) -> int:
    """Locate the header row: first line with enough delimited fields."""
    for idx, line in enumerate(lines):
        if line.count(DELIMITER) >= _MIN_HEADER_FIELDS:
            return idx
    raise IneSourceError("Could not locate a delimited header row in PREP data")


def parse_csv(text: str) -> list[dict[str, str]]:
    """Parse PREP CSV text into a list of row dicts.

    Skips leading metadata lines and uses the detected header for keys.
    """
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return []
    header_idx = _find_header_index(lines)
    reader = csv.DictReader(lines[header_idx:], delimiter=DELIMITER)
    return [dict(row) for row in reader]


def fetch_results(url: str, member: str | None = None) -> list[dict[str, Any]]:
    """End-to-end: download ZIP → extract CSV → parse to rows."""
    zip_bytes = download_zip(url)
    text = extract_csv_text(zip_bytes, member=member)
    return parse_csv(text)
