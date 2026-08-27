# api/app/partnerize_client.py
# TV/TVC credential-neutral compatibility surface.

from typing import Any, Dict, Optional

from fastapi import HTTPException

TVC_ROUTE_REQUIRED = "TVC_ADMITTED_PROVIDER_ROUTE_REQUIRED"


async def _request(
    method: str,
    path: str,
    params: Optional[Dict[str, Any]] = None,
) -> Any:
    """Fail closed until an admitted TV/TVC Partnerize provider route exists."""

    del method, path, params
    raise HTTPException(
        status_code=503,
        detail=(
            "TVC_ADMITTED_PROVIDER_ROUTE_REQUIRED: StegSports-CFP has no "
            "Partnerize credential or direct provider-execution authority"
        ),
    )


async def get_networks() -> Any:
    """Compatibility helper for the historical Partnerize network surface."""

    return await _request("GET", "/network")


async def get_conversions(
    campaign_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> Any:
    """Compatibility helper for historical Partnerize conversion queries."""

    params: Dict[str, Any] = {}
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    if limit is not None:
        params["limit"] = limit
    if offset is not None:
        params["offset"] = offset
    path = f"/v3/brand/campaigns/{campaign_id}/conversions/bulk"
    return await _request("GET", path, params=params)
