#!/usr/bin/env python
"""Light load test: concurrent activist captures (SPA-4 Task 10, AC-9.1).

Simulates N activists logging in and POSTing a /registros capture in parallel
using asyncio + httpx.  Reports throughput, latency percentiles, and errors.

Requirements
------------
- httpx >= 0.24  (already a project dep via fastapi[all] / starlette)
- asyncio (stdlib)
- No new dependencies added.

Usage
-----
  # Quickstart — 20 concurrent activists, default localhost target
  python scripts/loadtest_capture.py

  # Custom concurrency and target
  python scripts/loadtest_capture.py --workers 50 --base-url https://qa.example.com

  # Use the seeded credentials from conftest (for local dev)
  python scripts/loadtest_capture.py --workers 10

  # Print every request result
  python scripts/loadtest_capture.py --verbose

Environment variables (override CLI args)
-----------------------------------------
  LOADTEST_BASE_URL   Base URL (default http://localhost:8000)
  LOADTEST_WORKERS    Number of concurrent workers (default 20)
  LOADTEST_EMAIL      Base email prefix; worker i uses {prefix}+{i}@...
                      (defaults to activista1@alpha.gov for every worker —
                       OK for local dev where all share one test account)
  LOADTEST_PASSWORD   Password (default password123)
  LOADTEST_CAMPAIGN   X-Campaign-Id header value

Safety
------
  - Defaults to localhost — NEVER hits prod without explicit --base-url.
  - Each worker uses a unique client_uuid so captures are idempotent on retry.
  - Workers clean up their registros after the run (best-effort DELETE).
"""
from __future__ import annotations

import argparse
import asyncio
import os
import statistics
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

try:
    import httpx
except ImportError:  # pragma: no cover
    raise SystemExit(
        "httpx is required for the load test.\n"
        "Install it with:  pip install httpx"
    )

# ---------------------------------------------------------------------------
# Defaults (safe: localhost only)
# ---------------------------------------------------------------------------

DEFAULT_BASE_URL = "http://localhost:8000"
DEFAULT_WORKERS = 20
DEFAULT_EMAIL = "activista1@alpha.gov"
DEFAULT_PASSWORD = "password123"
DEFAULT_CAMPAIGN_ID = "11111111-1111-1111-1111-111111111111"  # ALPHA_CAMPAIGN_ID
API_PREFIX = "/api"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class WorkerResult:
    worker_id: int
    login_ok: bool = False
    capture_ok: bool = False
    login_ms: float = 0.0
    capture_ms: float = 0.0
    error: Optional[str] = None
    registro_id: Optional[str] = None
    delete_ok: bool = False


@dataclass
class Summary:
    total: int = 0
    login_failures: int = 0
    capture_successes: int = 0
    capture_failures: int = 0
    login_latencies: list[float] = field(default_factory=list)
    capture_latencies: list[float] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Worker coroutine
# ---------------------------------------------------------------------------


async def run_worker(
    worker_id: int,
    client: httpx.AsyncClient,
    email: str,
    password: str,
    campaign_id: str,
    verbose: bool,
) -> WorkerResult:
    result = WorkerResult(worker_id=worker_id)

    # --- Login ---
    t0 = time.perf_counter()
    try:
        resp = await client.post(
            f"{API_PREFIX}/auth/login",
            json={"email": email, "password": password},
            timeout=10.0,
        )
        result.login_ms = (time.perf_counter() - t0) * 1000
        if resp.status_code != 200:
            result.error = f"login {resp.status_code}: {resp.text[:120]}"
            if verbose:
                print(f"[W{worker_id}] LOGIN FAIL {resp.status_code}")
            return result
        token = resp.json()["access_token"]
        result.login_ok = True
        if verbose:
            print(f"[W{worker_id}] login OK ({result.login_ms:.0f}ms)")
    except Exception as exc:
        result.error = f"login exception: {exc}"
        result.login_ms = (time.perf_counter() - t0) * 1000
        return result

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Campaign-Id": campaign_id,
    }

    # --- Capture ---
    client_uuid = str(uuid.uuid4())
    t1 = time.perf_counter()
    try:
        cap = await client.post(
            f"{API_PREFIX}/registros",
            json={
                "nombre_completo": f"Loadtest Worker {worker_id}",
                "consentimiento": True,
                "client_uuid": client_uuid,
            },
            headers=headers,
            timeout=10.0,
        )
        result.capture_ms = (time.perf_counter() - t1) * 1000
        if cap.status_code == 201:
            result.capture_ok = True
            result.registro_id = cap.json().get("id")
        else:
            result.error = f"capture {cap.status_code}: {cap.text[:120]}"
        if verbose:
            status = "OK" if result.capture_ok else f"FAIL({cap.status_code})"
            print(f"[W{worker_id}] capture {status} ({result.capture_ms:.0f}ms)")
    except Exception as exc:
        result.error = f"capture exception: {exc}"
        result.capture_ms = (time.perf_counter() - t1) * 1000

    # --- Cleanup: delete the registro (best-effort, don't count in timing) ---
    if result.registro_id:
        try:
            del_resp = await client.delete(
                f"{API_PREFIX}/registros/{result.registro_id}",
                headers=headers,
                timeout=5.0,
            )
            result.delete_ok = del_resp.status_code == 204
        except Exception:
            pass  # best-effort

    return result


# ---------------------------------------------------------------------------
# Main async orchestrator
# ---------------------------------------------------------------------------


async def run_loadtest(
    base_url: str,
    workers: int,
    email: str,
    password: str,
    campaign_id: str,
    verbose: bool,
) -> Summary:
    summary = Summary(total=workers)

    async with httpx.AsyncClient(base_url=base_url, follow_redirects=True) as client:
        wall_start = time.perf_counter()

        tasks = [
            asyncio.create_task(
                run_worker(i, client, email, password, campaign_id, verbose)
            )
            for i in range(workers)
        ]
        results: list[WorkerResult] = await asyncio.gather(*tasks)

        wall_elapsed = time.perf_counter() - wall_start

    for r in results:
        if r.login_ok:
            summary.login_latencies.append(r.login_ms)
        else:
            summary.login_failures += 1
        if r.capture_ok:
            summary.capture_successes += 1
            summary.capture_latencies.append(r.capture_ms)
        else:
            summary.capture_failures += 1
        if r.error:
            summary.errors.append(f"W{r.worker_id}: {r.error}")

    # Print report
    def _pct(data: list[float], p: int) -> float:
        if not data:
            return 0.0
        return statistics.quantiles(data, n=100)[p - 1]

    print()
    print("=" * 60)
    print("  Ágora Load Test — Activist Capture")
    print("=" * 60)
    print(f"  Target:          {base_url}")
    print(f"  Workers:         {workers}")
    print(f"  Wall time:       {wall_elapsed:.2f}s")
    print(
        f"  Throughput:      {summary.capture_successes / wall_elapsed:.1f} captures/s"
    )
    print()
    print("  Login")
    print(f"    OK:            {len(summary.login_latencies)}/{workers}")
    if summary.login_latencies:
        print(f"    p50:           {_pct(summary.login_latencies, 50):.0f}ms")
        print(f"    p95:           {_pct(summary.login_latencies, 95):.0f}ms")
        print(f"    max:           {max(summary.login_latencies):.0f}ms")
    print()
    print("  Capture")
    print(f"    OK:            {summary.capture_successes}/{workers}")
    print(f"    Errors:        {summary.capture_failures}")
    if summary.capture_latencies:
        print(f"    p50:           {_pct(summary.capture_latencies, 50):.0f}ms")
        print(f"    p95:           {_pct(summary.capture_latencies, 95):.0f}ms")
        print(f"    max:           {max(summary.capture_latencies):.0f}ms")
    if summary.errors:
        print()
        print("  Errors (first 10):")
        for e in summary.errors[:10]:
            print(f"    - {e}")
    print("=" * 60)

    return summary


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Light concurrent load test for /registros activist capture.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Defaults to localhost:8000 — safe to run without arguments.\n\n"
            "Example:\n"
            "  python scripts/loadtest_capture.py --workers 50 --base-url https://qa.example.com\n"
        ),
    )
    p.add_argument(
        "--base-url",
        default=os.getenv("LOADTEST_BASE_URL", DEFAULT_BASE_URL),
        help=f"API base URL (default: {DEFAULT_BASE_URL})",
    )
    p.add_argument(
        "--workers",
        type=int,
        default=int(os.getenv("LOADTEST_WORKERS", DEFAULT_WORKERS)),
        help=f"Number of concurrent activist workers (default: {DEFAULT_WORKERS})",
    )
    p.add_argument(
        "--email",
        default=os.getenv("LOADTEST_EMAIL", DEFAULT_EMAIL),
        help=f"Activist email (default: {DEFAULT_EMAIL})",
    )
    p.add_argument(
        "--password",
        default=os.getenv("LOADTEST_PASSWORD", DEFAULT_PASSWORD),
        help="Activist password",
    )
    p.add_argument(
        "--campaign",
        default=os.getenv("LOADTEST_CAMPAIGN", DEFAULT_CAMPAIGN_ID),
        help="X-Campaign-Id header value",
    )
    p.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-worker request outcomes",
    )
    return p


def main() -> None:
    args = _build_parser().parse_args()

    print(
        f"Starting load test: {args.workers} workers → {args.base_url} "
        f"as {args.email}"
    )
    summary = asyncio.run(
        run_loadtest(
            base_url=args.base_url,
            workers=args.workers,
            email=args.email,
            password=args.password,
            campaign_id=args.campaign,
            verbose=args.verbose,
        )
    )
    if summary.capture_failures > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
