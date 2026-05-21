from fastapi import APIRouter, Request

from ..auth import current_advertiser_id

router = APIRouter(prefix="/api", tags=["campaigns"])


@router.get("/campaigns")
async def list_campaigns(request: Request):
    advertiser_id = await current_advertiser_id(request)
    pool = request.app.state.pool
    rows = await pool.fetch(
        """
        SELECT campaign_id, name, channel, objective, daily_budget_usd
        FROM campaigns
        WHERE advertiser_id = $1
        ORDER BY daily_budget_usd DESC
        """,
        advertiser_id,
    )
    return [dict(r) for r in rows]


@router.get("/perf/by-campaign")
async def perf_by_campaign(request: Request):
    """Spend, revenue, ROAS rolled up per campaign over the last 12 weeks."""
    advertiser_id = await current_advertiser_id(request)
    pool = request.app.state.pool
    rows = await pool.fetch(
        """
        SELECT c.campaign_id,
               c.name,
               c.channel,
               SUM(p.spend_usd)::float    AS spend,
               SUM(p.revenue_usd)::float  AS revenue,
               SUM(p.impressions)::bigint AS impressions,
               SUM(p.clicks)::bigint      AS clicks,
               SUM(p.conversions)::bigint AS conversions
        FROM campaign_daily_perf p
        JOIN campaigns c USING (campaign_id)
        WHERE p.advertiser_id = $1
        GROUP BY c.campaign_id, c.name, c.channel
        ORDER BY spend DESC
        """,
        advertiser_id,
    )
    out = []
    for r in rows:
        d = dict(r)
        d["roas"] = round(d["revenue"] / d["spend"], 2) if d["spend"] else 0.0
        d["cpa"] = round(d["spend"] / d["conversions"], 2) if d["conversions"] else None
        out.append(d)
    return out


@router.get("/perf/daily")
async def perf_daily(request: Request):
    """Daily spend + revenue, summed across all campaigns for the tenant."""
    advertiser_id = await current_advertiser_id(request)
    pool = request.app.state.pool
    rows = await pool.fetch(
        """
        SELECT date::text                   AS date,
               SUM(spend_usd)::float        AS spend,
               SUM(revenue_usd)::float      AS revenue,
               SUM(impressions)::bigint     AS impressions,
               SUM(conversions)::bigint     AS conversions
        FROM campaign_daily_perf
        WHERE advertiser_id = $1
        GROUP BY date
        ORDER BY date
        """,
        advertiser_id,
    )
    return [dict(r) for r in rows]


@router.get("/perf/by-channel")
async def perf_by_channel(request: Request):
    advertiser_id = await current_advertiser_id(request)
    pool = request.app.state.pool
    rows = await pool.fetch(
        """
        SELECT channel,
               SUM(spend_usd)::float    AS spend,
               SUM(revenue_usd)::float  AS revenue,
               SUM(impressions)::bigint AS impressions
        FROM campaign_daily_perf
        WHERE advertiser_id = $1
        GROUP BY channel
        ORDER BY spend DESC
        """,
        advertiser_id,
    )
    return [dict(r) for r in rows]
