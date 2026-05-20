from fastapi import APIRouter, Request, Depends

from ..auth import current_advertiser_id, is_agency_admin, get_email_and_token

router = APIRouter(prefix="/api", tags=["advertisers"])


@router.get("/me")
async def me(request: Request):
    email, _ = get_email_and_token(request)
    adv_id = await current_advertiser_id(request)
    admin = await is_agency_admin(request)
    return {"email": email, "advertiser_id": adv_id, "is_agency_admin": admin}


@router.get("/advertisers")
async def list_advertisers(request: Request):
    pool = request.app.state.pool
    rows = await pool.fetch(
        """
        SELECT advertiser_id, name, tier, brand_color, monthly_budget_usd
        FROM advertisers
        ORDER BY name
        """
    )
    return [dict(r) for r in rows]


@router.get("/advertisers/{advertiser_id}")
async def get_advertiser(advertiser_id: str, request: Request):
    pool = request.app.state.pool
    row = await pool.fetchrow(
        "SELECT * FROM advertisers WHERE advertiser_id = $1",
        advertiser_id,
    )
    if not row:
        return {"error": "not found"}
    return dict(row)
