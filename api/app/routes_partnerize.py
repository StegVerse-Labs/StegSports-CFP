# api/app/routes_partnerize.py
# [SCW-AFFILIATE-PARTNERIZE-ROUTES v2025-12-03-01]

from typing import Any, Dict, Optional

from fastapi import APIRouter, Query

from .partnerize_client import partnerize_get

router = APIRouter()


@router.get(
    "/networks",
    summary="List Partnerize networks for the current user",
    tags=["partnerize"],
)
async def list_networks() -> Dict[str, Any]:
    """
    Simple wrapper around GET /network

    This returns the list of networks your Partnerize user has access to.
    """
    return await partnerize_get("/network")


@router.get(
    "/campaigns/{campaign_id}/conversions",
    summary="Get bulk conversions for a specific campaign",
    tags=["partnerize"],
)
async def campaign_conversions(
    campaign_id: int,
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(100, ge=1, le=1000, description="Pagination limit"),
    start_date: Optional[str] = Query(
        None,
        description="Start date filter in YYYY-MM-DD format (optional)",
    ),
    end_date: Optional[str] = Query(
        None,
        description="End date filter in YYYY-MM-DD format (optional)",
    ),
) -> Dict[str, Any]:
    """
    Wrapper around:

        GET /v3/brand/campaigns/{campaignId}/conversions/bulk

    Exposes a few common filters: offset, limit, start_date, end_date.
    """
    params: Dict[str, Any] = {
        "offset": offset,
        "limit": limit,
    }
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date

    path = f"/v3/brand/campaigns/{campaign_id}/conversions/bulk"
    return await partnerize_get(path, params=params)


@router.get(
    "/raw",
    summary="Generic Partnerize GET proxy (safe, read-only)",
    tags=["partnerize"],
)
async def partnerize_raw(
    path: str = Query(
        ...,
        description="Relative Partnerize path such as 'network' or 'v2/campaigns'",
        examples=["network", "v2/campaigns"],
    ),
    offset: Optional[int] = Query(None, ge=0),
    limit: Optional[int] = Query(None, ge=1, le=1000),
) -> Dict[str, Any]:
    """
    Very small generic read-only passthrough for exploratory use.

    Example:
        /v1/partnerize/raw?path=network
        /v1/partnerize/raw?path=v2/campaigns&offset=0&limit=50
    """
    params: Dict[str, Any] = {}
    if offset is not None:
        params["offset"] = offset
    if limit is not None:
        params["limit"] = limit

    return await partnerize_get(path, params=params)
