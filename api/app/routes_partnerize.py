# api/app/routes_partnerize.py
# [CFP-PARTNERIZE-ROUTES v2025-12-03-01]

from typing import Any, Optional

from fastapi import APIRouter, Path, Query

from . import partnerize_client

router = APIRouter(tags=["partnerize"])


@router.get("/networks", summary="List Partnerize networks")
async def list_networks() -> Any:
    """
    Returns the raw Partnerize `/network` payload for the configured user.

    This is useful to verify that PARTNERIZE_APP_KEY / PARTNERIZE_USER_API_KEY
    are correct and to see which networks are available.
    """
    return await partnerize_client.get_networks()


@router.get(
    "/campaigns/{campaign_id}/conversions",
    summary="List conversions for a campaign (proxy to Partnerize)",
)
async def list_conversions(
    campaign_id: str = Path(..., description="Partnerize campaign ID"),
    start_date: Optional[str] = Query(
        None,
        description="Start date (YYYY-MM-DD) in Partnerize report timezone.",
        example="2025-12-01",
    ),
    end_date: Optional[str] = Query(
        None,
        description="End date (YYYY-MM-DD) in Partnerize report timezone.",
        example="2025-12-31",
    ),
    limit: Optional[int] = Query(
        300,
        ge=1,
        le=1000,
        description="Maximum records to return in one page (Partnerize limit dependent).",
    ),
    offset: Optional[int] = Query(
        0,
        ge=0,
        description="Offset into the result set for paging.",
    ),
) -> Any:
    """
    Thin proxy around Partnerize bulk conversions.

    Returns whichever JSON Partnerize gives us. The front-end dashboard
    computes aggregate metrics (totals, averages) from this payload.
    """
    return await partnerize_client.get_conversions(
        campaign_id=campaign_id,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )
