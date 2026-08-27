# api/app/routes_partnerize.py
# [CFP-PARTNERIZE-ROUTES v2025-12-03-01]

import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(tags=["partnerize"])

TVC_ROUTE_REQUIRED = "TVC_ADMITTED_PROVIDER_ROUTE_REQUIRED"
PARTNERIZE_BASE_URL = TVC_ROUTE_REQUIRED


def _has_keys() -> bool:
    """StegSports never owns Partnerize credential material."""

    return False


def _auth_header() -> Dict[str, str]:
    """Retained compatibility name; consumer-side auth construction is retired."""

    raise HTTPException(
        status_code=503,
        detail="TVC_ADMITTED_PROVIDER_ROUTE_REQUIRED: Partnerize authentication belongs inside TV/TVC",
    )


async def _get(path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Fail closed until TVC returns a bounded non-secret Partnerize result."""

    del path, params
    raise HTTPException(
        status_code=503,
        detail="TVC_ADMITTED_PROVIDER_ROUTE_REQUIRED: direct Partnerize execution is retired",
    )


# -------------------------------------------------------------------
# Status
# -------------------------------------------------------------------


@router.get("/status", summary="Partnerize env + basic /network ping")
async def partnerize_status() -> Dict[str, Any]:
    env_ok = _has_keys()
    base_url = PARTNERIZE_BASE_URL
    network_ping_ok = False
    network_count: Optional[int] = None
    error: Optional[str] = None
    exec_time: Optional[str] = None

    if env_ok:
        t0 = time.time()
        try:
            data = await _get("/network")
            exec_time = data.get("execution_time")
            network_count = data.get("count")
            if network_count is None:
                nets = data.get("networks") or []
                network_count = len(nets)
            network_ping_ok = True
        except HTTPException as he:
            error = str(he.detail)[:400]
        except Exception as e:
            error = str(e)[:400]
        dt = time.time() - t0
        if not exec_time:
            exec_time = f"{dt:.3f}s"

    return {
        "ok": env_ok and network_ping_ok,
        "env_ok": env_ok,
        "network_ping_ok": network_ping_ok,
        "network_count": network_count,
        "execution_time": exec_time,
        "base_url": base_url,
        "error": error,
    }


# -------------------------------------------------------------------
# Networks summary
# -------------------------------------------------------------------


@router.get("/networks/summary", summary="Flattened /network listing")
async def networks_summary() -> Dict[str, Any]:
    if not _has_keys():
        raise HTTPException(
            status_code=503,
            detail="TVC_ADMITTED_PROVIDER_ROUTE_REQUIRED",
        )

    data = await _get("/network")

    raw_networks = data.get("networks") or []
    items: List[Dict[str, Any]] = []

    for entry in raw_networks:
        n = entry.get("network") or entry
        items.append(
            {
                "id": n.get("network_id"),
                "name": n.get("network_name"),
                "description": n.get("network_description"),
                "locale": n.get("network_locale"),
            }
        )

    return {
        "ok": True,
        "count": len(items),
        "raw_count": data.get("count"),
        "execution_time": data.get("execution_time"),
        "items": items,
    }


# -------------------------------------------------------------------
# Conversions summary by campaign
# -------------------------------------------------------------------


@router.get(
    "/conversions/summary",
    summary="Conversions + revenue summary by campaign_id",
)
async def conversions_summary(
    campaign_ids: str = Query(
        ...,
        description="Comma-separated list of Partnerize campaign IDs.",
    ),
    days: int = Query(
        30,
        ge=1,
        le=365,
        description="Lookback window in days for conversions.",
    ),
) -> Dict[str, Any]:
    """
    Pull a rough conversions + revenue summary per campaign_id.

    NOTE: This is intentionally defensive:
    - If Partnerize path or shape changes, per-campaign 'error' is populated
    - We try a couple of obvious fields for revenue (commission_value, sale_amount, amount)
    """
    if not _has_keys():
        raise HTTPException(
            status_code=503,
            detail="Partnerize keys not configured (PARTNERIZE_APP_KEY / PARTNERIZE_API_KEY).",
        )

    ids = [c.strip() for c in campaign_ids.split(",") if c.strip()]
    if not ids:
        raise HTTPException(status_code=400, detail="No valid campaign_ids provided.")

    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days)
    start_iso = start_date.isoformat()
    end_iso = end_date.isoformat()

    window = {"start_date": start_iso, "end_date": end_iso}

    results: List[Dict[str, Any]] = []

    for cid in ids:
        path = f"/v3/brand/campaigns/{cid}/conversions/bulk"
        params = {
            # These are "good guess" params; adjust if Partnerize docs require different keys.
            "offset": 0,
            "limit": 500,
            "from": start_iso,
            "to": end_iso,
        }

        conv_count = 0
        revenue = 0.0
        currency: Optional[str] = None
        error: Optional[str] = None

        try:
            data = await _get(path, params=params)

            # Best guess for where conversions live
            items = data.get("conversions") or data.get("items") or []
            if isinstance(items, dict):
                # Sometimes it's {"conversions": {"items": [...]}}
                items = items.get("items") or []

            conv_count = len(items)

            for item in items:
                conv = item.get("conversion") or item
                # Try a few likely revenue fields
                raw_amount = (
                    conv.get("commission_value")
                    or conv.get("commission")
                    or conv.get("sale_amount")
                    or conv.get("amount")
                )
                if raw_amount is not None:
                    try:
                        revenue += float(raw_amount)
                    except Exception:
                        pass

                if not currency:
                    currency = conv.get("currency")

        except HTTPException as he:
            error = str(he.detail)[:300]
        except Exception as e:
            error = str(e)[:300]

        results.append(
            {
                "campaign_id": cid,
                "conversions": conv_count,
                "revenue": round(revenue, 2),
                "currency": currency,
                "error": error,
            }
        )

    return {
        "ok": True,
        "days": days,
        "window": window,
        "campaigns": results,
    }
