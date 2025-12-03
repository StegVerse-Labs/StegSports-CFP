# api/app/partnerize_client.py
# [CFP-PARTNERIZE-CLIENT v2025-12-03-01]

import os
import base64
from typing import Any, Dict, Optional

import httpx
from fastapi import HTTPException

PARTNERIZE_BASE_URL = os.getenv("PARTNERIZE_BASE_URL", "https://api.partnerize.com")

_APP_KEY = os.getenv("PARTNERIZE_APP_KEY")
_USER_API_KEY = os.getenv("PARTNERIZE_USER_API_KEY")


def _auth_header() -> Dict[str, str]:
    """
    Build the HTTP Basic Authorization header required by Partnerize.

    Username  = application_key
    Password  = user_api_key
    Header    = "Basic <base64(username:password)>"
    """
    if not _APP_KEY or not _USER_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="Partnerize keys not configured on server (PARTNERIZE_APP_KEY / PARTNERIZE_USER_API_KEY).",
        )

    token_raw = f"{_APP_KEY}:{_USER_API_KEY}".encode("utf-8")
    token_b64 = base64.b64encode(token_raw).decode("ascii")
    return {"Authorization": f"Basic {token_b64}"}


async def _request(
    method: str,
    path: str,
    params: Optional[Dict[str, Any]] = None,
) -> Any:
    """
    Small wrapper around httpx to call Partnerize and translate errors into HTTPException.
    """
    url = PARTNERIZE_BASE_URL.rstrip("/") + path
    headers = _auth_header()

    timeout = httpx.Timeout(20.0, connect=10.0)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.request(method, url, headers=headers, params=params)
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Partnerize connection error: {exc}",
        ) from exc

    if resp.status_code >= 400:
        detail = f"Partnerize error {resp.status_code}"
        try:
            data = resp.json()
            if isinstance(data, dict):
                msg = (
                    data.get("message")
                    or data.get("error")
                    or data.get("detail")
                    or data.get("faultstring")
                )
                if msg:
                    detail = f"{detail}: {msg}"
        except Exception:
            pass

        raise HTTPException(status_code=502, detail=detail)

    # Return JSON if possible, otherwise raw text.
    try:
        return resp.json()
    except ValueError:
        return resp.text


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


async def get_networks() -> Any:
    """
    GET /network

    Returns all networks the current Partnerize user has access to.
    """
    return await _request("GET", "/network")


async def get_conversions(
    campaign_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> Any:
    """
    GET /v3/brand/campaigns/{campaign_id}/conversions/bulk

    Thin proxy around the Partnerize bulk conversions endpoint.
    """
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
