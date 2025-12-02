# stubhub_client.py
# v2025-12-02-01 — StubHub application-only client
from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

import httpx

STUBHUB_CLIENT_ID = os.getenv("STUBHUB_CLIENT_ID")
STUBHUB_CLIENT_SECRET = os.getenv("STUBHUB_CLIENT_SECRET")
STUBHUB_SCOPE = os.getenv("STUBHUB_SCOPE", "read:events")

STUBHUB_AUTH_BASE = "https://account.stubhub.com"
# NOTE: Replace STUBHUB_EVENTS_PATH with the correct events endpoint path
# once you have final docs/access. This file is intentionally conservative.
STUBHUB_API_BASE = "https://api.stubhub.com"
STUBHUB_EVENTS_PATH = "/sellers/search/events/v3"  # placeholder


class StubHubConfigError(RuntimeError):
    pass


class StubHubAuthError(RuntimeError):
    pass


class StubHubAPIError(RuntimeError):
    pass


_token_cache: Dict[str, Any] = {
    "access_token": None,
    "expires_at": 0.0,
}


def _require_config() -> None:
    if not STUBHUB_CLIENT_ID or not STUBHUB_CLIENT_SECRET:
        raise StubHubConfigError(
            "StubHub credentials not configured. "
            "Set STUBHUB_CLIENT_ID and STUBHUB_CLIENT_SECRET in Render."
        )


async def _get_access_token() -> str:
    """
    Application-only OAuth2 (client_credentials).
    """
    _require_config()

    now = time.time()
    token = _token_cache.get("access_token")
    expires_at = float(_token_cache.get("expires_at") or 0.0)

    # Reuse valid token with 60s safety margin
    if token and expires_at - 60 > now:
        return token

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"{STUBHUB_AUTH_BASE}/oauth2/token",
            data={"grant_type": "client_credentials", "scope": STUBHUB_SCOPE},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            auth=(STUBHUB_CLIENT_ID, STUBHUB_CLIENT_SECRET),
        )

    if resp.status_code != 200:
        raise StubHubAuthError(
            f"StubHub auth failed {resp.status_code}: {resp.text[:200]}"
        )

    data = resp.json()
    token = data.get("access_token")
    if not token:
        raise StubHubAuthError("StubHub auth response missing access_token")

    expires_in = float(data.get("expires_in", 3600))
    _token_cache["access_token"] = token
    _token_cache["expires_at"] = now + expires_in
    return token


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
    Application-only search for events on StubHub.

    IMPORTANT: This uses a conservative, generic schema because StubHub's
    public docs are sparse. Once you have a live dev app and real responses,
    adjust `_normalize_event` and `STUBHUB_EVENTS_PATH` accordingly.
    """
    token = await _get_access_token()

    params: Dict[str, Any] = {
        "rows": per_page,
    }

    if query:
        params["q"] = query

    if city:
        params["city"] = city
    if state:
        params["state"] = state

    if lat is not None and lon is not None:
        params["latitude"] = lat
        params["longitude"] = lon
        if radius_miles is not None:
            params["radius"] = radius_miles

    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(
            f"{STUBHUB_API_BASE}{STUBHUB_EVENTS_PATH}",
            headers={"Authorization": f"Bearer {token}"},
            params=params,
        )

    if resp.status_code != 200:
        raise StubHubAPIError(
            f"StubHub API error {resp.status_code}: {resp.text[:200]}"
        )

    data = resp.json()
    # Many StubHub examples use "events" or "eventList"; handle both.
    events = data.get("events") or data.get("eventList") or []
    return [_normalize_event(e) for e in events]


def _normalize_event(raw: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map StubHub's event schema into the same compact format we use for SeatGeek.
    This will likely need a small tweak once we see real payloads.
    """
    venue = raw.get("venue") or raw.get("venueConfig") or {}
    pricing = raw.get("ticketInfo") or raw.get("pricing") or {}

    return {
        "provider": "stubhub",
        "id": str(raw.get("id") or raw.get("eventId")),
        "title": raw.get("name") or raw.get("description"),
        "datetime_local": raw.get("eventDateUTC") or raw.get("eventDateLocal"),
        "url": raw.get("eventUrl") or raw.get("url"),
        "venue": {
            "name": venue.get("name"),
            "city": venue.get("city"),
            "state": venue.get("state"),
            "country": venue.get("country"),
        },
        "pricing": {
            "lowest_price": pricing.get("minPrice") or pricing.get("lowPrice"),
            "lowest_price_good_deals": None,
        },
        # Potential hook for seat-level rows/sections if StubHub exposes them
        "seatmeta": raw.get("seatAttributes"),
    }
