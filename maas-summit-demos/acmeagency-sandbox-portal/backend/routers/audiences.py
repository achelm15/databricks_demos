from fastapi import APIRouter, Request

from ..auth import current_advertiser_id

router = APIRouter(prefix="/api", tags=["audiences"])


@router.get("/audiences")
async def list_audiences(request: Request):
    advertiser_id = await current_advertiser_id(request)
    pool = request.app.state.pool
    rows = await pool.fetch(
        """
        SELECT segment_id, name, size, overlap_score
        FROM audience_segments
        WHERE advertiser_id = $1
        ORDER BY size DESC
        """,
        advertiser_id,
    )
    return [dict(r) for r in rows]
