"""Scale-to-zero cost panel.

Models the savings AcmeAgency captures by letting low-tier tenants idle their
Lakebase compute when nobody is logged in. The "true" billing comes from
`system.billing.usage`, but during the workshop we use a deterministic synthetic
model so the panel always has a story to tell.

The headline metric:
   savings_this_month = sum( capacity_dbu_rate * idle_hours_this_month ) per tenant
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict

from databricks.sdk import WorkspaceClient
from fastapi import APIRouter, Request

from ..auth import is_agency_admin
from ..config import get_settings

router = APIRouter(prefix="/api", tags=["cost"])

# Approximate $/hr per capacity tier (CU_1=$0.50/hr, CU_2=$1.00/hr, CU_4=$2.00/hr)
HOURLY_USD: Dict[str, float] = {"CU_1": 0.50, "CU_2": 1.00, "CU_4": 2.00, "CU_8": 4.00}
HOURS_IN_MONTH = 24 * 30

# Per-tier behavior model
TIER_BEHAVIOR = {
    # tier        active_hours_per_day  business_days
    "enterprise": (24, 30),     # always warm
    "growth":     (12, 22),     # warm during business hours weekdays
    "starter":    (3,  20),     # only when an advertiser logs in
}


def _idle_hours_saved(tier: str) -> float:
    active_hrs_day, active_days = TIER_BEHAVIOR.get(tier, (24, 30))
    active = active_hrs_day * active_days
    return max(0.0, HOURS_IN_MONTH - active)


@router.get("/cost/summary")
async def cost_summary(request: Request):
    """Top-line numbers for the cost panel.

    Returns spend if every advertiser was always-on, current spend with scale-to-zero,
    and the dollar savings.
    """
    settings = get_settings()
    pool = request.app.state.pool
    # Get all advertisers with their tier
    rows = await pool.fetch(
        "SELECT advertiser_id, name, tier FROM advertisers ORDER BY tier, name"
    )

    rate = HOURLY_USD["CU_1"]
    always_on = 0.0
    actual = 0.0
    per_tenant = []
    for r in rows:
        tier = r["tier"]
        active_hrs_day, active_days = TIER_BEHAVIOR.get(tier, (24, 30))
        active_hours = active_hrs_day * active_days
        always_on_cost = HOURS_IN_MONTH * rate
        actual_cost = active_hours * rate
        saved = always_on_cost - actual_cost
        always_on += always_on_cost
        actual += actual_cost
        per_tenant.append({
            "advertiser_id": r["advertiser_id"],
            "name": r["name"],
            "tier": tier,
            "active_hours_this_month": active_hours,
            "idle_hours_saved": _idle_hours_saved(tier),
            "always_on_usd": round(always_on_cost, 2),
            "actual_usd": round(actual_cost, 2),
            "saved_usd": round(saved, 2),
        })

    branch_count, branch_cost = await _live_branch_cost(settings.lakebase_instance, rate)

    return {
        "currency": "USD",
        "rate_per_hour_usd": rate,
        "always_on_usd": round(always_on, 2),
        "actual_usd": round(actual, 2),
        "saved_usd": round(always_on - actual, 2),
        "savings_pct": round((always_on - actual) / always_on * 100, 1) if always_on else 0.0,
        "tenant_count": len(rows),
        "live_branch_count": branch_count,
        "live_branch_cost_usd_per_hour": round(branch_cost, 2),
        "per_tenant": per_tenant,
        "as_of": datetime.now(timezone.utc).isoformat(),
    }


async def _live_branch_cost(parent_instance: str, base_rate: float) -> tuple[int, float]:
    """Sum the hourly cost of all *running* branches off the parent instance."""
    w = WorkspaceClient()
    try:
        resp = w.api_client.do("GET", "/api/2.0/database/instances")
    except Exception:
        return (0, 0.0)
    count, total = 0, 0.0
    for inst in resp.get("database_instances", []):
        parent = inst.get("parent_instance_ref")
        if not parent or parent.get("name") != parent_instance:
            continue
        if inst.get("state") not in ("AVAILABLE", "STARTING"):
            continue
        count += 1
        total += HOURLY_USD.get(inst.get("capacity", "CU_1"), base_rate)
    return (count, total)
