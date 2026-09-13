"""Checks the /dashboard static mount coexists with the API routes.

Uses the shared SQLite harness from test_cv_backend. The dashboard build must
exist (dashboard/dist) for the mount to be active.
"""

from __future__ import annotations

from pathlib import Path

from test_cv_backend import client  # noqa: F401 (shared engine + override)

DASHBOARD_DIST = Path(__file__).resolve().parent.parent / "dashboard" / "dist"


def test_dashboard_static_served():
    if not DASHBOARD_DIST.is_dir():
        # build missing -> the fallback route answers instead
        assert client.get("/dashboard").status_code == 200
        return
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "MineGuard" in response.text


def test_dashboard_summary_router_not_shadowed_by_mount():
    # The mount is appended AFTER include_router, so /dashboard/summary must
    # still hit the API router rather than the static file mount.
    response = client.get("/dashboard/summary")
    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("application/json")
    assert "active_worker_count" in response.text


def test_admin_simulator_unaffected():
    response = client.get("/admin-simulator")
    assert response.status_code in (200,)