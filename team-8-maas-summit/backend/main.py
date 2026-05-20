"""FastAPI entrypoint for the MAAS Summit Team 8 demo app.

Routes:
  /api/me                  — who am I (email, advertiser, admin?)
  /api/advertisers         — agency admin: list tenants
  /api/campaigns           — current tenant's campaigns
  /api/perf/by-campaign    — spend/revenue/ROAS per campaign
  /api/perf/daily          — daily spend/revenue trend
  /api/perf/by-channel     — channel mix
  /api/audiences           — segment list
  /api/pacing              — pacing rows
  /api/pacing/summary      — KPI strip data
  /api/branches            — list branches off the parent instance
  /api/branches POST       — spawn a sandbox/onboarding branch
  /api/branches/{name} DELETE — tear it down
  /api/cost/summary        — scale-to-zero savings panel
  /api/health              — readiness probe
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from databricks.sdk import WorkspaceClient

from .config import get_settings
from .db import LakebasePool
from .routers import advertisers, audiences, branches, campaigns, cost, pacing

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("maas-team8")


class LakebaseTokenMiddleware(BaseHTTPMiddleware):
    """Capture the user's OAuth token from the Apps proxy on every request.

    Tokens expire ~1h, so we MUST refresh before checking pool.available.
    """

    async def dispatch(self, request: Request, call_next):
        h = request.headers
        email = (h.get("X-Forwarded-Email")
                 or h.get("X-Forwarded-Preferred-Username")
                 or h.get("X-Forwarded-User"))
        token = h.get("x-forwarded-access-token")

        # Local dev fallback: synthesize from env using SDK auth
        settings = get_settings()
        if not (email and token) and settings.local_dev_email:
            email = settings.local_dev_email
            token = _get_local_dev_token()

        pool = request.app.state.pool
        if email and token:
            pool.update_token(token)
            if not pool.available:
                pool.capture_user_token(email, token)
                try:
                    await pool.init()
                except Exception as e:
                    log.exception("pool init failed")
                    return JSONResponse({"error": f"pool init: {e}"}, status_code=503)
        return await call_next(request)


def _get_local_dev_token() -> str | None:
    """For local dev: get a fresh OAuth access token via the workspace SDK."""
    try:
        w = WorkspaceClient()
        # databricks-sdk authenticate() returns an Authorization header dict
        hdrs = w.config.authenticate()
        bearer = hdrs.get("Authorization", "")
        if bearer.startswith("Bearer "):
            return bearer[len("Bearer "):]
    except Exception:
        log.exception("local dev token fetch failed")
    return None


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="MAAS Summit Team 8 — Multi-Tenant Self-Serve Reporting")

    app.state.pool = LakebasePool(settings.lakebase_instance, settings.lakebase_database)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(LakebaseTokenMiddleware)

    app.include_router(advertisers.router)
    app.include_router(campaigns.router)
    app.include_router(audiences.router)
    app.include_router(pacing.router)
    app.include_router(branches.router)
    app.include_router(cost.router)

    @app.get("/api/health")
    async def health(request: Request):
        pool = request.app.state.pool
        return {
            "status": "ok",
            "pool_available": pool.available,
            "lakebase_instance": settings.lakebase_instance,
            "lakebase_database": settings.lakebase_database,
        }

    @app.on_event("shutdown")
    async def _shutdown():
        await app.state.pool.close()

    # Static React app (no-build, served from frontend/ directly)
    static_dir = Path(settings.static_dir)
    if static_dir.exists():
        # serve /public/* (favicons etc) and any top-level file (index.html, app.js, styles.css)
        public_dir = static_dir / "public"
        if public_dir.exists():
            app.mount("/public", StaticFiles(directory=public_dir), name="public")

        @app.get("/{full_path:path}")
        async def spa(full_path: str):
            target = static_dir / full_path
            if target.is_file():
                return FileResponse(target)
            # also support /favicon.svg style references that live under public/
            pub = public_dir / full_path if public_dir.exists() else None
            if pub and pub.is_file():
                return FileResponse(pub)
            return FileResponse(static_dir / "index.html")
    else:
        @app.get("/")
        async def root():
            return {"status": "ok", "note": "static_dir not found", "static_dir": str(static_dir)}

    return app


app = create_app()
