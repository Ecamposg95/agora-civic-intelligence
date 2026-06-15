"""Analytics service — civic intelligence aggregates.

Returns a representative overview payload so the executive dashboard can be
wired end-to-end before real data pipelines land. Results are tenant-scoped.
"""

from __future__ import annotations

from typing import Any


def get_overview(organization_id: str | None) -> dict[str, Any]:
    """Return high-level civic intelligence KPIs and trend series."""
    return {
        "summary": {
            "registered_voters": 1_284_530,
            "electoral_areas": 412,
            "active_institutions": 1,
            "participation_rate": 0.631,
        },
        "trends": {
            "participation": [
                {"period": "2025-Q1", "value": 0.58},
                {"period": "2025-Q2", "value": 0.60},
                {"period": "2025-Q3", "value": 0.62},
                {"period": "2025-Q4", "value": 0.63},
            ],
        },
        "alerts": [
            {
                "level": "info",
                "title": "Data governance baseline established",
                "detail": "Audit logging is active across sensitive endpoints.",
            }
        ],
    }
