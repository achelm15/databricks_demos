"""Tenant resolution from Databricks Apps proxy headers.

In production (deployed app), every request carries:
  - X-Forwarded-Email           : the logged-in user's email
  - x-forwarded-access-token    : the user's short-lived OAuth token

We map email -> advertiser_id via the `tenant_membership` table in Lakebase.
For the workshop, AcmeAgency is a single Databricks workspace with one user-tenant
mapping per advertiser (you log in as a different user, see different advertiser).

For *local dev* without the Apps proxy, set `LOCAL_DEV_EMAIL` and the request will
synthesize the headers from the env.
"""
from __future__ import annotations

from typing import Optional, Tuple

from fastapi import Header, HTTPException, Request

from .config import get_settings


def get_email_and_token(request: Request) -> Tuple[str, Optional[str]]:
    settings = get_settings()
    h = request.headers
    email = (h.get("X-Forwarded-Email")
             or h.get("X-Forwarded-Preferred-Username")
             or h.get("X-Forwarded-User"))
    token = h.get("x-forwarded-access-token")
    if not email and settings.local_dev_email:
        email = settings.local_dev_email
    if not email:
        email = "anonymous"
    return email, token


async def current_advertiser_id(request: Request) -> str:
    """Resolve the current user's advertiser_id.

    Order:
      1. Explicit `X-Advertiser-Override` header (agency-admin "view as tenant" toggle)
      2. Lookup in `tenant_membership` table
      3. Fall back to settings.default_advertiser_id
    """
    settings = get_settings()
    override = request.headers.get("X-Advertiser-Override")
    if override:
        return override

    email, _ = get_email_and_token(request)
    pool = getattr(request.app.state, "pool", None)
    if pool is not None and pool.available:
        row = await pool.fetchrow(
            "SELECT advertiser_id FROM tenant_membership WHERE email = $1 LIMIT 1",
            email,
        )
        if row:
            return row["advertiser_id"]
    return settings.default_advertiser_id


async def is_agency_admin(request: Request) -> bool:
    """Agency admins (AcmeAgency employees) can switch tenants and view costs."""
    email, _ = get_email_and_token(request)
    return email.endswith("@acmeagency.com") or email.endswith("@databricks.com")
