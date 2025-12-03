# api/app/routes_partnerize.py
# [SCW-PARTNERIZE-ROUTES v2025-12-03-01]
#
# Thin Partnerize proxy layer for SCW-API.
# - Handles auth header construction
# - Exposes a few safe, read-only endpoints for the dashboard.

import base64
import os
from typing import Any, Dict, Optional

import httpx
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/v1/partnerize", tags=["partnerize"])

# -------------------------------------------------------------------
# Config helpers
# -------------------------------------------------------------------

PARTNERIZE_BASE_URL = os.getenv("PARTNERIZE_BASE_URL", "https://api.partnerize.com")

APP_KEY = os.getenv("PARTNERIZE_APPLICATION_KEY")  # "application_key" in docs
USER_API_KEY = os.getenv("PARTNERIZE_USER_API_KEY")  # "user_api_key" in docs


def _auth_header() -> str:
    """
    Build the Basic auth header value like:
      Authorization: Basic base64(application_key:user_api_key)
    """
    if not APP_KEY or not USER_API_KEY:
        raise RuntimeError(
            "Partnerize credentials are not configured. "
            "Set PARTNERIZE_APPLICATION_KEY and PARTNERIZE_USER_API_KEY."
        )

    raw = f"{APP_KEY}:{USER_API_KEY}".encode("utf-8")
    token = base64.b64encode(raw).decode("ascii")
    return f"Basic {token}"


async def _partnerize_get(path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Minimal GET wrapper for Partnerize.
    Path examples:
      "/network"
      "/v2/campaigns"
    """
    if not path.startswith("/"):
        path = "/" + path

    url = PARTNERIZE_BASE_URL.rstrip("/") + path

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                url,
                headers={"Authorization": _auth_header()},
                params=params or {},
            )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Partnerize request failed: {exc}") from exc

    if resp.status_code == 401:
        raise HTTPException(status_code=502, detail="Partnerize auth failed (401). Check keys.")
    if resp.status_code == 403:
        raise HTTPException(status_code=502, detail="Partnerize access denied (403).")
    if resp.status_code >= 500:
        raise HTTPException(status_code=502, detail=f"Partnerize upstream error: {resp.status_code}")

    try:
        return resp.json()
    except ValueError:
        raise HTTPException(status_code=502, detail="Partnerize returned non-JSON response.")


# -------------------------------------------------------------------
# Public endpoints
# -------------------------------------------------------------------


@router.get("/status", summary="Partnerize config & health summary")
async def partnerize_status() -> Dict[str, Any]:
    """
    Lightweight status endpoint for the dashboard.

    - Verifies that env vars exist.
    - Optionally pings /network to confirm credentials.
    """
    env_ok = bool(APP_KEY and USER_API_KEY)

    status: Dict[str, Any] = {
        "env_ok": env_ok,
        "base_url": PARTNERIZE_BASE_URL,
        "has_app_key": bool(APP_KEY),
        "has_user_api_key": bool(USER_API_KEY),
        "network_ping_ok": False,
        "network_count": None,
        "error": None,
    }

    if not env_ok:
        status["error"] = "Missing PARTNERIZE_APPLICATION_KEY or PARTNERIZE_USER_API_KEY."
        return status

    try:
        data = await _partnerize_get("/network")
        status["network_ping_ok"] = True
        status["network_count"] = data.get("count")
    except HTTPException as exc:
        status["error"] = f"Upstream error: {exc.detail}"
    except Exception as exc:  # pragma: no cover - defensive
        status["error"] = f"Unexpected error: {exc}"

    return status


@router.get("/networks", summary="List Partnerize networks (raw)")
async def partnerize_networks() -> Dict[str, Any]:
    """
    Thin passthrough to GET /network.

    Returns exactly what Partnerize returns so we don't lose information.
    """
    return await _partnerize_get("/network")


@router.get("/networks/summary", summary="Simplified networks summary")
async def partnerize_networks_summary() -> Dict[str, Any]:
    """
    Friendly summary for UI:
    - count
    - list of {id, name, locale}
    """
    data = await _partnerize_get("/network")

    items = []
    for item in data.get("networks", []):
        n = item.get("network", {})
        items.append(
            {
                "id": n.get("network_id"),
                "name": n.get("network_name"),
                "description": n.get("network_description"),
                "locale": n.get("network_locale"),
                "default_campaign_id": n.get("default_campaign_id"),
            }
        )

    return {
        "count": len(items),
        "items": items,
        "raw_count": data.get("count"),
        "execution_time": data.get("execution_time"),
    }


@router.get("/raw", summary="Safe GET passthrough to Partnerize")
async def partnerize_raw(path: str, limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """
    Very small, *read-only* passthrough for GET operations while we iterate.

    Usage example:
      /v1/partnerize/raw?path=/network
      /v1/partnerize/raw?path=/v2/some/endpoint&limit=50&offset=0

    NOTE: Only allows GET and only to paths starting with '/network' or '/v'.
    """
    if not (path.startswith("/network") or path.startswith("/v")):
        raise HTTPException(status_code=400, detail="Path must start with '/network' or '/v'.")

    params: Dict[str, Any] = {"limit": limit, "offset": offset}
    return await _partnerize_get(path, params=params)
