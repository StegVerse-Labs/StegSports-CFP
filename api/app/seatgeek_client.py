# seatgeek_client.py
# v2025-12-02-01 — SeatGeek application-only client
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import httpx

SEATGEEK_CLIENT_ID = os.getenv("SEATGEEK_CLIENT_ID")
SEATGEEK_BASE_URL = "https://api.seatgeek.com/2"


class SeatGeekConfigError(RuntimeError):
    pass


class SeatGeekAPIError(RuntimeError):
    pass


def _require_config() -> None:
    if not SEATGEEK_CLIENT_ID:
        raise SeatGeekConfigError(
            "SEATGEEK_CLIENT_ID is not set. "
            "Configure it in your Render environment for the API service."
        )


async def search_events(
    *,
    query: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    radius_miles: Optional[int] = None,
    per_page: int = 20,
) -> List[Dict[str, Any]]:
    """
    Thin wrapper around SeatGeek events endpoint.

    We only use a small, normalized subset of fields so that the rest of
    the SCW code doesn't care which provider the results came from.
    """
    _require_config()

    params: Dict[str, Any] = {
        "client_id": SEATGEEK_CLIENT_ID,
        "per_page": per_page,
    }

    if query:
        params["q"] = query

    if city:
        params["venue.city"] = city
    if state:
        params["venue.state"] = state

    if lat is not None and lon is not None:
        params["lat"] = lat
        params["lon"] = lon
        if radius_miles is not None:
            params["range"] = f"{radius_miles}mi"

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{SEATGEEK_BASE_URL}/events", params=params)

    if resp.status_code != 200:
        raise SeatGeekAPIError(
            f"SeatGeek API error {resp.status_code}: {resp.text[:200]}"
        )

    data = resp.json()
    events = data.get("events", []) or []
    return [_normalize_event(e) for e in events]


def _normalize_event(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map SeatGeek's event schema into a compact, provider-agnostic format.
    """
    venue = raw.get("venue") or {}
    stats = raw.get("stats") or {}

    return {
        "provider": "seatgeek",
        "id": str(raw.get("id")),
        "title": raw.get("title"),
        "datetime_local": raw.get("datetime_local"),
        "url": raw.get("url"),
        "venue": {
            "name": venue.get("name"),
            "city": venue.get("city"),
            "state": venue.get("state"),
            "country": venue.get("country"),
        },
        "pricing": {
            "lowest_price": stats.get("lowest_price"),
            "lowest_price_good_deals": stats.get("lowest_price_good_deals"),
        },
        # Placeholder for seat-level info; SeatGeek doesn't expose that in this endpoint
        "seatmeta": None,
    }
