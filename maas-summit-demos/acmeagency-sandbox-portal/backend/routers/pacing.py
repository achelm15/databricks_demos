from fastapi import APIRouter, Request

from ..auth import current_advertiser_id

router = APIRouter(prefix="/api", tags=["pacing"])


@router.get("/pacing")
async def list_pacing(request: Request):
    advertiser_id = await current_advertiser_id(request)
    pool = request.app.state.pool
    rows = await pool.fetch(
        """
        SELECT p.campaign_id,
               c.name           AS campaign_name,
               c.channel,
               p.monthly_budget_usd::float AS monthly_budget,
               p.ftd_spend_usd::float     AS ftd_spend,
               p.expected_pace::float,
               p.actual_pace::float,
               p.days_remaining,
               p.health
        FROM pacing_metrics p
        JOIN campaigns c USING (campaign_id)
        WHERE p.advertiser_id = $1
        ORDER BY p.monthly_budget_usd DESC
        """,
        advertiser_id,
    )
    return [dict(r) for r in rows]


@router.get("/pacing/summary")
async def pacing_summary(request: Request):
    """High-level pacing health for the KPI strip."""
    advertiser_id = await current_advertiser_id(request)
    pool = request.app.state.pool
    row = await pool.fetchrow(
        """
        SELECT
          COUNT(*)::int                                                AS campaigns,
          SUM(monthly_budget_usd)::float                               AS total_budget,
          SUM(ftd_spend_usd)::float                                    AS total_ftd,
          SUM(CASE WHEN health = 'on_pace'     THEN 1 ELSE 0 END)::int AS on_pace,
          SUM(CASE WHEN health = 'underpacing' THEN 1 ELSE 0 END)::int AS underpacing,
          SUM(CASE WHEN health = 'overpacing'  THEN 1 ELSE 0 END)::int AS overpacing
        FROM pacing_metrics
        WHERE advertiser_id = $1
        """,
        advertiser_id,
    )
    return dict(row) if row else {}
