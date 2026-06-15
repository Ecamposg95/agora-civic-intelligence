# Phase 1 — External Intel (IEEM + World Bank) & Module Enrichment — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:dispatching-parallel-agents to implement this plan. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Add a robust backend proxy for external data, two REAL sources (IEEM Numeralia for Estado de México, World Bank national indicators), a reusable chart-primitives library, and real audit-driven enrichment of Analytics/Dashboard — in the all-black command-center style.

**Architecture:** Backend `intel` router proxies external sources server-side (reuses `integrations/ine/base.py` httpx wrapper with retries) with a small TTL cache; new `intel` integrations parse upstreams to clean JSON. Frontend consumes via `useAsync` + `DataState` (graceful failure) and renders with new Recharts-based chart primitives. Analytics gains real tenant-scoped aggregations over `audit_logs`.

**Tech Stack:** FastAPI, SQLAlchemy 2.0, Pydantic v2, httpx, pytest; Vite + React 18 + TS + Tailwind, Recharts, react-router, Zustand.

**Reference spec:** `docs/superpowers/specs/2026-06-15-external-intel-and-enrichment-design.md`

**Conventions:** backend tests from `backend/`: `cd backend && python3 -m pytest -q`. Tenant scoping: `ctx.is_superadmin` → no filter else `ctx.organization_id`. Deps `DbSession`, `Tenant`. Frontend build: `cd frontend && npm run build`. All API calls via `apiClient`. All-black tokens: `accent` cyan, `amber`, `card-premium`, `hud-corners`, `font-display`, `font-mono`. Use `useAsync` (`@/hooks/useAsync`) + `DataState` (`@/components/ui/DataState`) + `PageHeader`. Honesty: real data labelled to source; previews keep `PreviewBanner`.

---

## Parallelization (for dispatching-parallel-agents)

Three streams touch DISJOINT files and can run concurrently:
- **Stream A (backend intel):** Tasks A1–A4 — `backend/app/integrations/intel/*`, `backend/app/routers/intel.py`, `backend/app/main.py` (router reg), `backend/tests/test_intel.py`.
- **Stream B (backend analytics):** Tasks B1–B2 — `backend/app/services/analytics_service.py`, `backend/app/routers/analytics.py`, `backend/tests/test_analytics.py`.
- **Stream C (frontend charts):** Task C1 — `frontend/src/components/charts/*` only.

Conflict note: A edits `main.py`; B edits `analytics.py`; they do not overlap. Run A, B, C in parallel. **Integration tasks D1–D4 depend on A+B+C and must run AFTER** (they touch `registry.ts`, pages, `api/intel.ts`). Within D, D1/D2 (module pages) are independent of D3/D4 (enrichment) and may parallelize, but all D tasks edit shared frontend files (`registry.ts`) so prefer sequential or careful coordination. Quick wins to land first: **C1, B1–B2** (fast, pure value), then **A**.

---

# Stream A — Backend intel proxy + IEEM + World Bank

### Task A1: TTL cache helper

**Files:**
- Create: `backend/app/integrations/intel/__init__.py` (empty)
- Create: `backend/app/integrations/intel/cache.py`
- Test: `backend/tests/test_intel_cache.py`

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_intel_cache.py
from app.integrations.intel.cache import TTLCache


def test_cache_returns_cached_value_within_ttl():
    calls = {"n": 0}
    cache = TTLCache(ttl_seconds=100, now=lambda: 1000.0)

    def loader():
        calls["n"] += 1
        return {"v": calls["n"]}

    assert cache.get_or_set("k", loader) == {"v": 1}
    assert cache.get_or_set("k", loader) == {"v": 1}  # cached, loader not called again
    assert calls["n"] == 1


def test_cache_expires_after_ttl():
    t = {"now": 1000.0}
    calls = {"n": 0}
    cache = TTLCache(ttl_seconds=10, now=lambda: t["now"])

    def loader():
        calls["n"] += 1
        return calls["n"]

    assert cache.get_or_set("k", loader) == 1
    t["now"] = 1011.0  # past ttl
    assert cache.get_or_set("k", loader) == 2
    assert calls["n"] == 2
```

- [ ] **Step 2: Run RED** — `cd backend && python3 -m pytest tests/test_intel_cache.py -q` → FAIL (module missing).

- [ ] **Step 3: Implement**

```python
# backend/app/integrations/intel/cache.py
"""Tiny in-process TTL cache for external-source responses."""

from __future__ import annotations

import time
from typing import Any, Callable


class TTLCache:
    def __init__(self, ttl_seconds: float = 900.0, now: Callable[[], float] = time.monotonic) -> None:
        self._ttl = ttl_seconds
        self._now = now
        self._store: dict[str, tuple[float, Any]] = {}

    def get_or_set(self, key: str, loader: Callable[[], Any]) -> Any:
        hit = self._store.get(key)
        now = self._now()
        if hit is not None and (now - hit[0]) < self._ttl:
            return hit[1]
        value = loader()
        self._store[key] = (now, value)
        return value

    def clear(self) -> None:
        self._store.clear()
```

- [ ] **Step 4: Run GREEN** — `cd backend && python3 -m pytest tests/test_intel_cache.py -q` → PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/integrations/intel/__init__.py backend/app/integrations/intel/cache.py backend/tests/test_intel_cache.py
git commit -m "feat(intel): TTL cache helper"
```

---

### Task A2: IEEM Numeralia integration (CSV → JSON)

**Files:**
- Create: `backend/app/integrations/intel/ieem.py`
- Test: `backend/tests/test_intel_ieem.py`

Context: IEEM publishes stable CSVs at `https://dorganizacion.ieem.org.mx/numeralia/docs/<File>.csv`. Confirmed: `Municipios_EdoMex_2025.csv` → headers `MUNICIPIO,NOMBRE DEL MUNICIPIO`, comma-delimited UTF-8, 125 rows. We fetch bytes via `ine/base.get_bytes` (retries) and parse with the stdlib `csv` module. A dataset registry maps a stable key → file URL.

- [ ] **Step 1: Write the failing test** (parses CSV bytes without network, via injected fetcher)

```python
# backend/tests/test_intel_ieem.py
from app.integrations.intel import ieem


CSV = b"MUNICIPIO,NOMBRE DEL MUNICIPIO\r\n1,ACAMBAY\r\n2,ACOLMAN\r\n"


def test_datasets_registry_has_municipios():
    keys = {d["key"] for d in ieem.list_datasets()}
    assert "municipios" in keys


def test_fetch_dataset_parses_csv_rows():
    result = ieem.fetch_dataset("municipios", fetch=lambda url: CSV)
    assert result["key"] == "municipios"
    assert result["columns"] == ["MUNICIPIO", "NOMBRE DEL MUNICIPIO"]
    assert result["rows"][0] == {"MUNICIPIO": "1", "NOMBRE DEL MUNICIPIO": "ACAMBAY"}
    assert result["count"] == 2
    assert "source" in result and "ieem" in result["source"].lower()


def test_unknown_dataset_raises():
    import pytest
    with pytest.raises(KeyError):
        ieem.fetch_dataset("nope", fetch=lambda url: CSV)
```

- [ ] **Step 2: Run RED** — `python3 -m pytest tests/test_intel_ieem.py -q` → FAIL.

- [ ] **Step 3: Implement**

```python
# backend/app/integrations/intel/ieem.py
"""IEEM (Instituto Electoral del Estado de México) Numeralia — real CSV datasets.

Files are stable CSV downloads (no token, no API). We fetch bytes server-side
(avoids CORS) and parse with the stdlib csv module. Add datasets here as their
exact file names are confirmed from the numeralia sub-pages.
"""

from __future__ import annotations

import csv
import io
from typing import Any, Callable

from app.integrations.ine.base import get_bytes

BASE = "https://dorganizacion.ieem.org.mx/numeralia/docs"
SOURCE = "IEEM Numeralia — Registro Federal de Electores (Estado de México)"

# key -> (label, filename). Confirmed: municipios. Others to confirm at impl time
# by reading the sub-pages; municipios is the verified working case.
DATASETS: dict[str, dict[str, str]] = {
    "municipios": {"label": "Catálogo de municipios", "file": "Municipios_EdoMex_2025.csv"},
}


def list_datasets() -> list[dict[str, str]]:
    return [{"key": k, "label": v["label"]} for k, v in DATASETS.items()]


def _parse_csv(raw: bytes) -> tuple[list[str], list[dict[str, str]]]:
    text = raw.decode("utf-8-sig")  # handle BOM
    reader = csv.reader(io.StringIO(text))
    rows = [r for r in reader if any(cell.strip() for cell in r)]
    if not rows:
        return [], []
    header = [h.strip() for h in rows[0]]
    out: list[dict[str, str]] = []
    for r in rows[1:]:
        out.append({header[i]: (r[i].strip() if i < len(r) else "") for i in range(len(header))})
    return header, out


def fetch_dataset(
    key: str, *, fetch: Callable[[str], bytes] | None = None
) -> dict[str, Any]:
    if key not in DATASETS:
        raise KeyError(key)
    meta = DATASETS[key]
    url = f"{BASE}/{meta['file']}"
    fetcher = fetch or (lambda u: get_bytes(u))
    columns, rows = _parse_csv(fetcher(url))
    return {
        "key": key,
        "label": meta["label"],
        "columns": columns,
        "rows": rows,
        "count": len(rows),
        "source": SOURCE,
        "url": url,
    }
```

- [ ] **Step 4: Run GREEN** — `python3 -m pytest tests/test_intel_ieem.py -q` → PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/integrations/intel/ieem.py backend/tests/test_intel_ieem.py
git commit -m "feat(intel): IEEM Numeralia CSV datasets (real, EdoMex)"
```

---

### Task A3: World Bank integration (JSON indicators)

**Files:**
- Create: `backend/app/integrations/intel/worldbank.py`
- Test: `backend/tests/test_intel_worldbank.py`

Context: World Bank API `https://api.worldbank.org/v2/country/MX/indicator/<CODE>?format=json&per_page=100`. Response is `[meta, [ {date, value, indicator:{id,value}}, ... ]]`. No token, reliable. We fetch via `ine/base.get_json` and normalize to `{indicator, label, points:[{year, value}]}` sorted ascending, dropping null values.

- [ ] **Step 1: Write the failing test** (normalizes a sample payload via injected fetcher)

```python
# backend/tests/test_intel_worldbank.py
from app.integrations.intel import worldbank

PAYLOAD = [
    {"page": 1, "pages": 1},
    [
        {"date": "2022", "value": 1.0, "indicator": {"id": "NY.GDP.MKTP.CD", "value": "GDP"}},
        {"date": "2021", "value": None, "indicator": {"id": "NY.GDP.MKTP.CD", "value": "GDP"}},
        {"date": "2020", "value": 2.0, "indicator": {"id": "NY.GDP.MKTP.CD", "value": "GDP"}},
    ],
]


def test_indicators_registry_nonempty():
    assert len(worldbank.list_indicators()) >= 3
    assert all({"code", "label"} <= set(i) for i in worldbank.list_indicators())


def test_fetch_indicator_normalizes_sorted_dropping_nulls():
    r = worldbank.fetch_indicator("NY.GDP.MKTP.CD", fetch=lambda url, params: PAYLOAD)
    assert r["indicator"] == "NY.GDP.MKTP.CD"
    assert r["points"] == [{"year": 2020, "value": 2.0}, {"year": 2022, "value": 1.0}]
    assert r["latest"] == {"year": 2022, "value": 1.0}
```

- [ ] **Step 2: Run RED** — `python3 -m pytest tests/test_intel_worldbank.py -q` → FAIL.

- [ ] **Step 3: Implement**

```python
# backend/app/integrations/intel/worldbank.py
"""World Bank indicators for Mexico (national time series). No token; reliable."""

from __future__ import annotations

from typing import Any, Callable

from app.integrations.ine.base import get_json

BASE = "https://api.worldbank.org/v2/country/MX/indicator"
SOURCE = "World Bank Open Data"

INDICATORS: dict[str, str] = {
    "NY.GDP.MKTP.CD": "PIB (USD corrientes)",
    "SP.POP.TOTL": "Población total",
    "SL.UEM.TOTL.ZS": "Desempleo (% fuerza laboral)",
    "FP.CPI.TOTL.ZG": "Inflación (% anual)",
    "SI.POV.NAHC": "Pobreza (% nacional)",
}


def list_indicators() -> list[dict[str, str]]:
    return [{"code": c, "label": label} for c, label in INDICATORS.items()]


def fetch_indicator(
    code: str, *, fetch: Callable[[str, dict[str, Any]], Any] | None = None
) -> dict[str, Any]:
    url = f"{BASE}/{code}"
    params = {"format": "json", "per_page": 20000}
    fetcher = fetch or (lambda u, p: get_json(u, params=p))
    payload = fetcher(url, params)
    series = payload[1] if isinstance(payload, list) and len(payload) > 1 and payload[1] else []
    points = [
        {"year": int(row["date"]), "value": float(row["value"])}
        for row in series
        if row.get("value") is not None and str(row.get("date", "")).isdigit()
    ]
    points.sort(key=lambda p: p["year"])
    return {
        "indicator": code,
        "label": INDICATORS.get(code, code),
        "points": points,
        "latest": points[-1] if points else None,
        "source": SOURCE,
    }
```

- [ ] **Step 4: Run GREEN** — `python3 -m pytest tests/test_intel_worldbank.py -q` → PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/integrations/intel/worldbank.py backend/tests/test_intel_worldbank.py
git commit -m "feat(intel): World Bank indicators for Mexico (real)"
```

---

### Task A4: intel router (+ register) with cache & graceful errors

**Files:**
- Create: `backend/app/routers/intel.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_intel_api.py`

- [ ] **Step 1: Write the failing test** (uses dependency override to inject stub integrations is overkill; instead test routing + auth + graceful error by monkeypatching the integration functions)

```python
# backend/tests/test_intel_api.py
import app.routers.intel as intel_router
from app.integrations.ine.base import IneSourceError

from .conftest import auth_headers


def test_intel_requires_auth(client):
    assert client.get("/api/intel/worldbank/indicators").status_code == 401


def test_worldbank_indicators_list(client):
    headers = auth_headers(client, "admin@alpha.gov")
    r = client.get("/api/intel/worldbank/indicators", headers=headers)
    assert r.status_code == 200
    assert any(i["code"] == "SP.POP.TOTL" for i in r.json()["items"])


def test_ieem_dataset_success(client, monkeypatch):
    headers = auth_headers(client, "admin@alpha.gov")
    monkeypatch.setattr(
        intel_router.ieem, "fetch_dataset",
        lambda key, **kw: {"key": key, "label": "X", "columns": ["A"], "rows": [{"A": "1"}], "count": 1, "source": "IEEM", "url": "u"},
    )
    r = client.get("/api/intel/ieem/municipios", headers=headers)
    assert r.status_code == 200
    assert r.json()["count"] == 1


def test_upstream_failure_returns_502(client, monkeypatch):
    headers = auth_headers(client, "admin@alpha.gov")
    def boom(code, **kw):
        raise IneSourceError("down")
    monkeypatch.setattr(intel_router.worldbank, "fetch_indicator", boom)
    intel_router.CACHE.clear()
    r = client.get("/api/intel/worldbank/indicator/SP.POP.TOTL", headers=headers)
    assert r.status_code == 502
    assert "error" in r.json()
```

- [ ] **Step 2: Run RED** — `python3 -m pytest tests/test_intel_api.py -q` → FAIL.

- [ ] **Step 3: Implement the router**

```python
# backend/app/routers/intel.py
"""External intelligence proxy — server-side fetch of public data sources.

Fetches happen server-side (no CORS), with bounded retries (in the integration
layer) + a short TTL cache here. Upstream failures surface as 502 with the
standard error envelope so the frontend can show a graceful retry.
"""

from typing import Any

from fastapi import APIRouter, HTTPException, status

from app.dependencies import Tenant
from app.integrations.intel import ieem, worldbank
from app.integrations.intel.cache import TTLCache
from app.integrations.ine.base import IneSourceError

router = APIRouter(prefix="/intel", tags=["intel"])

CACHE = TTLCache(ttl_seconds=900.0)


@router.get("/ieem/datasets", summary="List IEEM (EdoMex) datasets")
def ieem_datasets(ctx: Tenant) -> dict[str, Any]:
    return {"items": ieem.list_datasets()}


@router.get("/ieem/{dataset}", summary="IEEM dataset (real CSV)")
def ieem_dataset(dataset: str, ctx: Tenant) -> dict[str, Any]:
    try:
        return CACHE.get_or_set(f"ieem:{dataset}", lambda: ieem.fetch_dataset(dataset))
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown dataset '{dataset}'")
    except IneSourceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"IEEM source unavailable: {exc}")


@router.get("/worldbank/indicators", summary="List World Bank indicators")
def worldbank_indicators(ctx: Tenant) -> dict[str, Any]:
    return {"items": worldbank.list_indicators()}


@router.get("/worldbank/indicator/{code}", summary="World Bank indicator series (real)")
def worldbank_indicator(code: str, ctx: Tenant) -> dict[str, Any]:
    try:
        return CACHE.get_or_set(f"wb:{code}", lambda: worldbank.fetch_indicator(code))
    except IneSourceError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"World Bank source unavailable: {exc}")
```

- [ ] **Step 4: Register in `backend/app/main.py`**

Add `intel` to the import tuple:
```python
from app.routers import (
    analytics,
    audit,
    auth,
    health,
    intel,
    maps,
    organizations,
    sources,
    users,
)
```
And to `_register_routers`:
```python
    for module in (health, auth, users, organizations, maps, analytics, sources, audit, intel):
        app.include_router(module.router, prefix=prefix)
```

- [ ] **Step 5: Run GREEN** — `cd backend && python3 -m pytest -q` → PASS (all).

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/intel.py backend/app/main.py backend/tests/test_intel_api.py
git commit -m "feat(intel): /api/intel router (IEEM + World Bank) with cache + 502 degradation"
```

---

# Stream B — Backend analytics enrichment (real audit aggregations)

### Task B1: aggregation functions in analytics_service (TDD)

**Files:**
- Modify: `backend/app/services/analytics_service.py`
- Test: `backend/tests/test_analytics.py` (extend)

Context: `audit_logs` has `action`, `actor_id`, `created_at`, `organization_id`. Add tenant-scoped aggregations. Keep them portable (group in Python from a tenant-scoped fetch, like the existing activity trend) to avoid dialect-specific SQL.

- [ ] **Step 1: Add the failing tests** (append to `backend/tests/test_analytics.py`)

```python
def test_overview_includes_breakdowns(client):
    from .conftest import auth_headers
    # generate a couple of audit events (logins)
    auth_headers(client, "admin@alpha.gov")
    headers = auth_headers(client, "admin@alpha.gov")
    body = client.get("/api/analytics/overview", headers=headers).json()
    assert "by_action" in body and isinstance(body["by_action"], list)
    assert all({"action", "count"} <= set(x) for x in body["by_action"])
    assert "by_actor" in body and isinstance(body["by_actor"], list)
    # at least the auth.login action present
    assert any(x["action"] == "auth.login" for x in body["by_action"])
```

- [ ] **Step 2: Run RED** — `python3 -m pytest tests/test_analytics.py::test_overview_includes_breakdowns -q` → FAIL (KeyError by_action).

- [ ] **Step 3: Implement** — in `backend/app/services/analytics_service.py`, inside `get_overview`, after the activity trend is built and before the return, add aggregations over the SAME tenant-scoped audit window already queried. Replace the activity loop so it also accumulates action/actor counts:

Add near the activity section (reuse `act_stmt` but also select action/actor):
```python
    # Replace the activity-only query with one that also yields action + actor.
    detail_stmt = select(AuditLog.created_at, AuditLog.action, AuditLog.actor_id).where(
        AuditLog.created_at >= start
    )
    if not ctx.is_superadmin:
        detail_stmt = detail_stmt.where(AuditLog.organization_id == ctx.organization_id)

    from collections import Counter
    action_counts: Counter[str] = Counter()
    actor_counts: Counter[str] = Counter()
    total_events = 0
    for created_at, action, actor_id in db.execute(detail_stmt).all():
        total_events += 1
        key = created_at.date().isoformat()
        if key in buckets:
            buckets[key] += 1
        action_counts[action] += 1
        if actor_id:
            actor_counts[actor_id] += 1

    by_action = [{"action": a, "count": c} for a, c in action_counts.most_common(8)]
    by_actor = [{"actor_id": a, "count": c} for a, c in actor_counts.most_common(5)]
```
Then remove the OLD activity-only loop (the one iterating `act_stmt` scalars and computing `total_events`) so there is exactly one pass. Keep `activity = [...]` built from `buckets` as before. Add `by_action` and `by_actor` to the returned dict:
```python
    return {
        "summary": {...unchanged...},
        "coverage": coverage,
        "trends": {"activity": activity},
        "by_action": by_action,
        "by_actor": by_actor,
        "alerts": alerts,
        "generated_at": now.isoformat(),
    }
```
(Keep all existing fields; only ADD `by_action`/`by_actor`. Ensure `act_stmt` is no longer referenced after removal, to avoid unused-variable issues.)

- [ ] **Step 4: Run GREEN** — `cd backend && python3 -m pytest -q` → PASS (all, incl. existing analytics tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/analytics_service.py backend/tests/test_analytics.py
git commit -m "feat(analytics): real by-action/by-actor breakdowns (tenant-scoped)"
```

### Task B2: expose breakdowns in frontend analytics type

**Files:**
- Modify: `frontend/src/types/analytics.ts`

- [ ] **Step 1: Extend the type** — add to `AnalyticsOverview`:
```ts
export interface AnalyticsOverview {
  summary: AnalyticsSummary;
  coverage: { level: string; count: number }[];
  trends: { activity: TrendPoint[] };
  by_action: { action: string; count: number }[];
  by_actor: { actor_id: string; count: number }[];
  alerts: AnalyticsAlert[];
  generated_at: string;
}
```
- [ ] **Step 2: Build** — `cd frontend && npm run build` → PASS. (Consumers added in D3.)
- [ ] **Step 3: Commit**
```bash
git add frontend/src/types/analytics.ts
git commit -m "feat(analytics): add by_action/by_actor to overview type"
```

---

# Stream C — Frontend chart primitives (quick win, pure frontend)

### Task C1: chart primitives (Donut, RadialGauge, Heatmap, StackedBars)

**Files:**
- Create: `frontend/src/components/charts/Donut.tsx`
- Create: `frontend/src/components/charts/RadialGauge.tsx`
- Create: `frontend/src/components/charts/Heatmap.tsx`
- Create: `frontend/src/components/charts/StackedBars.tsx`

All use the dark palette (axis `#52646d`, grid `#15242b`, tooltip bg `#06090c` border `#223a44` text `#e6f2f5`), cyan `#22d3ee` + amber `#f5b53d` + teal `#2dd4bf`. No `any`. Recharts for Donut/StackedBars; pure SVG/CSS for RadialGauge/Heatmap.

- [ ] **Step 1: Donut**
```tsx
// frontend/src/components/charts/Donut.tsx
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

export interface DonutDatum { name: string; value: number; color?: string; }
const PALETTE = ["#22d3ee", "#f5b53d", "#2dd4bf", "#7c8aa5", "#06b6d4", "#f4607a"];

export function Donut({ data, height = 200 }: { data: DonutDatum[]; height?: number }) {
  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer>
        <PieChart>
          <Pie data={data} dataKey="value" nameKey="name" innerRadius="58%" outerRadius="82%" paddingAngle={2} stroke="none">
            {data.map((d, i) => <Cell key={d.name} fill={d.color ?? PALETTE[i % PALETTE.length]} />)}
          </Pie>
          <Tooltip contentStyle={{ background: "#06090c", border: "1px solid #223a44", borderRadius: 10, color: "#e6f2f5", fontSize: 12 }} />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
```

- [ ] **Step 2: RadialGauge** (pure SVG, value 0..1)
```tsx
// frontend/src/components/charts/RadialGauge.tsx
export function RadialGauge({ value, label, size = 132 }: { value: number; label?: string; size?: number }) {
  const v = Math.max(0, Math.min(1, value));
  const r = size / 2 - 10;
  const c = 2 * Math.PI * r;
  const off = c * (1 - v);
  return (
    <div className="relative grid place-items-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#15242b" strokeWidth={10} />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#22d3ee" strokeWidth={10}
          strokeLinecap="round" strokeDasharray={c} strokeDashoffset={off}
          style={{ transition: "stroke-dashoffset .8s cubic-bezier(.16,1,.3,1)", filter: "drop-shadow(0 0 6px rgba(34,211,238,.5))" }} />
      </svg>
      <div className="absolute text-center">
        <div className="font-display text-2xl font-bold tabular-nums text-ink">{(v * 100).toFixed(0)}%</div>
        {label && <div className="text-[10px] uppercase tracking-wider text-ink-faint">{label}</div>}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Heatmap** (calendar/grid; data = {label, value}[])
```tsx
// frontend/src/components/charts/Heatmap.tsx
export interface HeatCell { label: string; value: number; }
export function Heatmap({ data, columns = 7 }: { data: HeatCell[]; columns?: number }) {
  const max = data.reduce((m, d) => Math.max(m, d.value), 0) || 1;
  return (
    <div className="grid gap-1.5" style={{ gridTemplateColumns: `repeat(${columns}, minmax(0,1fr))` }}>
      {data.map((d, i) => {
        const t = d.value / max;
        return (
          <div key={i} title={`${d.label}: ${d.value}`}
            className="aspect-square rounded-[3px] border border-line/60"
            style={{ background: `rgba(34,211,238,${0.08 + t * 0.8})` }} />
        );
      })}
    </div>
  );
}
```

- [ ] **Step 4: StackedBars**
```tsx
// frontend/src/components/charts/StackedBars.tsx
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export interface StackSeries { key: string; color: string; }
export function StackedBars({ data, series, xKey, height = 240 }: {
  data: Record<string, number | string>[]; series: StackSeries[]; xKey: string; height?: number;
}) {
  return (
    <div style={{ width: "100%", height }}>
      <ResponsiveContainer>
        <BarChart data={data} margin={{ left: -16, top: 8 }}>
          <CartesianGrid stroke="#15242b" vertical={false} />
          <XAxis dataKey={xKey} stroke="#52646d" tick={{ fontSize: 12 }} tickLine={false} axisLine={{ stroke: "#15242b" }} />
          <YAxis stroke="#52646d" tick={{ fontSize: 12 }} tickLine={false} axisLine={false} allowDecimals={false} />
          <Tooltip contentStyle={{ background: "#06090c", border: "1px solid #223a44", borderRadius: 10, color: "#e6f2f5", fontSize: 12 }} />
          {series.map((s) => <Bar key={s.key} dataKey={s.key} stackId="a" fill={s.color} radius={[2, 2, 0, 0]} />)}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
```

- [ ] **Step 5: Build + commit**

`cd frontend && npm run build` → PASS.
```bash
git add frontend/src/components/charts
git commit -m "feat(charts): dark chart primitives — Donut, RadialGauge, Heatmap, StackedBars"
```

---

# Stream D — Integration (AFTER A + B + C)

### Task D1: frontend intel data layer + IEEM module

**Files:**
- Create: `frontend/src/types/intel.ts`, `frontend/src/api/intel.ts`
- Create: `frontend/src/modules/ieem/IeemPage.tsx`
- Modify: `frontend/src/modules/registry.ts` (add active module)

- [ ] **Step 1: types + api**
```ts
// frontend/src/types/intel.ts
export interface IeemDataset { key: string; label: string; columns: string[]; rows: Record<string, string>[]; count: number; source: string; url: string; }
export interface IeemDatasetRef { key: string; label: string; }
export interface WbPoint { year: number; value: number; }
export interface WbIndicator { indicator: string; label: string; points: WbPoint[]; latest: WbPoint | null; source: string; }
export interface WbIndicatorRef { code: string; label: string; }
```
```ts
// frontend/src/api/intel.ts
import { apiClient } from "./client";
import type { IeemDataset, IeemDatasetRef, WbIndicator, WbIndicatorRef } from "@/types/intel";

export async function getIeemDatasets(): Promise<IeemDatasetRef[]> {
  const { data } = await apiClient.get<{ items: IeemDatasetRef[] }>("/intel/ieem/datasets");
  return data.items;
}
export async function getIeemDataset(key: string): Promise<IeemDataset> {
  const { data } = await apiClient.get<IeemDataset>(`/intel/ieem/${key}`);
  return data;
}
export async function getWbIndicators(): Promise<WbIndicatorRef[]> {
  const { data } = await apiClient.get<{ items: WbIndicatorRef[] }>("/intel/worldbank/indicators");
  return data.items;
}
export async function getWbIndicator(code: string): Promise<WbIndicator> {
  const { data } = await apiClient.get<WbIndicator>(`/intel/worldbank/indicator/${code}`);
  return data;
}
```

- [ ] **Step 2: IEEM page** (real; uses useAsync + DataState + PageHeader + searchable table)
```tsx
// frontend/src/modules/ieem/IeemPage.tsx
import { useMemo, useState } from "react";
import { getIeemDataset } from "@/api/intel";
import { AppLayout } from "@/components/layout/AppLayout";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { MetricCard } from "@/components/ui/MetricCard";
import { DataState } from "@/components/ui/DataState";
import { useAsync } from "@/hooks/useAsync";

const DATASETS = [{ key: "municipios", label: "Municipios" }];

export function IeemPage() {
  const [key, setKey] = useState("municipios");
  const [q, setQ] = useState("");
  const { data, loading, error, reload } = useAsync(() => getIeemDataset(key), [key]);
  const rows = useMemo(() => {
    if (!data) return [];
    if (!q.trim()) return data.rows;
    const needle = q.toLowerCase();
    return data.rows.filter((r) => Object.values(r).some((v) => v.toLowerCase().includes(needle)));
  }, [data, q]);

  return (
    <AppLayout title="Estado de México — Electoral" crumb="IEEM · Inteligencia Electoral">
      <PageHeader eyebrow="Inteligencia Electoral" title="Estado de México" accent="(IEEM)"
        subtitle="Estadística electoral oficial del Instituto Electoral del Estado de México (Registro Federal de Electores)."
        actions={data && (
          <MetricCard label={data.label} value={String(data.count)} />
        )} />
      <div className="mb-4 flex flex-wrap items-center gap-2">
        {DATASETS.map((d) => (
          <button key={d.key} onClick={() => { setKey(d.key); setQ(""); }}
            className={`rounded-lg border px-3 py-1.5 text-sm font-medium transition-all ${key === d.key ? "border-accent/40 bg-accent/10 text-accent shadow-glow-accent" : "border-line bg-bg-sunken text-ink-muted hover:text-ink"}`}>
            {d.label}
          </button>
        ))}
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Buscar…" className="field-input !py-2 ml-auto max-w-xs" />
      </div>
      <Card title={data?.label ?? "Dataset"} accentDot className="card-premium">
        <DataState loading={loading} error={error} onRetry={reload} isEmpty={!!data && data.rows.length === 0}>
          {data && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead><tr className="text-left text-xs uppercase tracking-wide text-ink-faint">
                  {data.columns.map((c) => <th key={c} className="px-2 py-2">{c}</th>)}
                </tr></thead>
                <tbody>
                  {rows.map((r, i) => (
                    <tr key={i} className="border-t border-line transition-colors hover:bg-panel-hover">
                      {data.columns.map((c) => <td key={c} className="px-2 py-2 font-mono text-ink-muted">{r[c]}</td>)}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </DataState>
        {data && <p className="mt-3 text-[11px] text-ink-faint">Fuente: {data.source}</p>}
      </Card>
    </AppLayout>
  );
}
```

- [ ] **Step 3: register module** — in `frontend/src/modules/registry.ts`, add lazy import and an `active` entry in the `inteligencia` section:
```ts
const Ieem = lazy(() => import("@/modules/ieem/IeemPage").then((m) => ({ default: m.IeemPage })));
// ...in MODULES, inteligencia section:
{ key: "ieem", path: "/ieem", label: "Estado de México (IEEM)", section: "inteligencia", icon: AnalyticsIcon, state: "active", element: Ieem },
```

- [ ] **Step 4: build + commit**
`cd frontend && npm run build` → PASS.
```bash
git add frontend/src/types/intel.ts frontend/src/api/intel.ts frontend/src/modules/ieem frontend/src/modules/registry.ts
git commit -m "feat(ieem): real Estado de México electoral module (/api/intel/ieem)"
```

### Task D2: World Bank module

**Files:**
- Create: `frontend/src/modules/worldbank/WorldBankPage.tsx`
- Modify: `frontend/src/modules/registry.ts`

- [ ] **Step 1: page** (real; indicator grid with line charts via ParticipationChart or a MiniLine; reuse existing `ParticipationChart` shape `{period,value}` by mapping points)
```tsx
// frontend/src/modules/worldbank/WorldBankPage.tsx
import { getWbIndicator } from "@/api/intel";
import { AppLayout } from "@/components/layout/AppLayout";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card } from "@/components/ui/Card";
import { DataState } from "@/components/ui/DataState";
import { ParticipationChart } from "@/components/dashboards/ParticipationChart";
import { useAsync } from "@/hooks/useAsync";

const CODES = [
  { code: "NY.GDP.MKTP.CD", label: "PIB (USD)" },
  { code: "SP.POP.TOTL", label: "Población" },
  { code: "FP.CPI.TOTL.ZG", label: "Inflación (%)" },
  { code: "SL.UEM.TOTL.ZS", label: "Desempleo (%)" },
];

function IndicatorCard({ code, label }: { code: string; label: string }) {
  const { data, loading, error, reload } = useAsync(() => getWbIndicator(code), [code]);
  const series = (data?.points ?? []).map((p) => ({ period: String(p.year), value: p.value }));
  return (
    <Card title={label} accentDot className="card-premium">
      <DataState loading={loading} error={error} onRetry={reload} isEmpty={!!data && series.length === 0}>
        {data && (
          <>
            <div className="mb-2 font-display text-2xl font-bold tabular-nums text-ink">
              {data.latest ? Intl.NumberFormat("es-MX", { notation: "compact" }).format(data.latest.value) : "—"}
              {data.latest && <span className="ml-2 text-xs text-ink-faint">{data.latest.year}</span>}
            </div>
            <ParticipationChart data={series} height={160} valueFormat="number" seriesLabel={label} />
          </>
        )}
      </DataState>
    </Card>
  );
}

export function WorldBankPage() {
  return (
    <AppLayout title="Indicadores Nacionales" crumb="World Bank · Macro">
      <PageHeader eyebrow="Contexto macro" title="Indicadores" accent="Nacionales"
        subtitle="Series macroeconómicas de México (Banco Mundial). Datos reales." />
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {CODES.map((c) => <IndicatorCard key={c.code} {...c} />)}
      </div>
    </AppLayout>
  );
}
```

- [ ] **Step 2: register** — add lazy import + active entry in `inteligencia` (or a new section):
```ts
const WorldBank = lazy(() => import("@/modules/worldbank/WorldBankPage").then((m) => ({ default: m.WorldBankPage })));
{ key: "worldbank", path: "/indicadores", label: "Indicadores Nacionales", section: "inteligencia", icon: AnalyticsIcon, state: "active", element: WorldBank },
```
- [ ] **Step 3: build + commit**
`cd frontend && npm run build` → PASS.
```bash
git add frontend/src/modules/worldbank frontend/src/modules/registry.ts
git commit -m "feat(worldbank): real national indicators module (/api/intel/worldbank)"
```

### Task D3: Enrich Analytics with breakdowns (real)

**Files:**
- Modify: `frontend/src/pages/AnalyticsPage.tsx`

- [ ] **Step 1: add charts** — using the new `Donut` (by_action) and a top-actors list/bar (by_actor) and the activity Heatmap, all from the real `data.by_action`/`by_actor`/`trends.activity`. Wrap each in the existing DataState pattern. Keep the existing chart. Example additions:
```tsx
import { Donut } from "@/components/charts/Donut";
import { Heatmap } from "@/components/charts/Heatmap";
// ...inside the grid, new cards:
// <Card title="Eventos por acción" accentDot><Donut data={(data?.by_action ?? []).map(a => ({ name: a.action, value: a.count }))} /></Card>
// <Card title="Actividad (heatmap)" accentDot><Heatmap data={(data?.trends.activity ?? []).map(p => ({ label: p.period, value: p.value }))} columns={7} /></Card>
// top actors: list data.by_actor with counts (actor_id sliced)
```
Build the full JSX consistent with the page's existing structure (PageHeader, reveal, card-premium). No fabricated data — only real fields.

- [ ] **Step 2: build + commit**
`cd frontend && npm run build` → PASS.
```bash
git add frontend/src/pages/AnalyticsPage.tsx
git commit -m "feat(analytics): real by-action donut, top actors, activity heatmap"
```

### Task D4: Enrich Dashboard (real gauge + heatmap + KPIs)

**Files:**
- Modify: `frontend/src/pages/DashboardPage.tsx`

- [ ] **Step 1: add** — a `RadialGauge` for a real ratio (e.g. coverage = electoral_areas mapped vs a sensible base, OR users active ratio — only if a real ratio exists; otherwise use an audit-activity gauge: today's events / window max), an activity `Heatmap` from `trends.activity`, and one or two more real KPI tiles (audit events in window from `by_action` sum). Use only real values; keep honesty. Keep the mini-map and existing panels. Wrap async-dependent regions in DataState (already present for overview).
- [ ] **Step 2: build + commit**
`cd frontend && npm run build` → PASS.
```bash
git add frontend/src/pages/DashboardPage.tsx
git commit -m "feat(dashboard): real gauge + activity heatmap + extra KPIs"
```

---

### Task E: Reachability verification + deploy

- [ ] **Step 1: Full backend tests** — `cd backend && python3 -m pytest -q` → PASS.
- [ ] **Step 2: Frontend build** — `cd frontend && npm run build` → PASS.
- [ ] **Step 3: Push** — `git push origin main`.
- [ ] **Step 4: Verify live reachability of the real upstreams FROM the Railway container** (not local, which is sandboxed). After deploy SUCCESS, with a superadmin token:
```bash
BASE="https://agora-gobtech.up.railway.app"; TOKEN=...
curl -s "$BASE/api/intel/ieem/municipios" -H "Authorization: Bearer $TOKEN" | python3 -c "import sys,json;d=json.load(sys.stdin);print('IEEM count:',d.get('count'))"
curl -s "$BASE/api/intel/worldbank/indicator/SP.POP.TOTL" -H "Authorization: Bearer $TOKEN" | python3 -c "import sys,json;d=json.load(sys.stdin);print('WB points:',len(d.get('points',[])))"
```
Expected: IEEM count ~125; WB points > 10. If an upstream is unreachable from Railway (502), the frontend already degrades via DataState — note it and (for IEEM) consider mirroring the CSV. Report results.

---

## Self-Review notes (addressed)

- **Spec coverage:** proxy framework (A1,A4), IEEM real (A2,A4,D1), World Bank real (A3,A4,D2), chart primitives (C1), real analytics/dashboard enrichment (B1,B2,D3,D4), graceful degradation (DataState reused; A4 502), honesty (real labelled to source; no fabricated values). Phase-1 scope only; DataMéxico/SIGE/token previews are later phases.
- **Type consistency:** `fetch_dataset(key, *, fetch=)`, `fetch_indicator(code, *, fetch=)` signatures match tests + router calls. Router attrs `intel_router.ieem`/`intel_router.worldbank`/`CACHE` match the monkeypatch tests. Frontend `getIeemDataset`/`getWbIndicator` match router paths `/intel/ieem/{key}`, `/intel/worldbank/indicator/{code}`. `AnalyticsOverview.by_action/by_actor` added in B2 and consumed in D3.
- **Placeholder scan:** IEEM dataset registry intentionally ships the CONFIRMED `municipios` file; the code note to add more datasets is a real follow-up, not a code placeholder — all shipped code is complete and tested.
- **Parallelism:** A/B/C disjoint; D after.
