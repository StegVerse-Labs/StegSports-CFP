import os
from typing import Any, Dict, List, Optional

import httpx

# ---------------------------------------------------------
# SeatGeek client (application-only style)
#
# This is intentionally thin and conservative. It assumes the
# classic pattern where SeatGeek accepts client_id/client_secret
# as query parameters. Once you have final docs from SeatGeek,
# you can adjust AUTH_MODE / params in one place.
# ---------------------------------------------------------

SEATGEEK_BASE_URL = os.getenv("SEATGEEK_BASE_URL", "https://api.seatgeek.com/2")
SEATGEEK_CLIENT_ID = os.getenv("SEATGEEK_CLIENT_ID", "")
SEATGEEK_CLIENT_SECRET = os.getenv("SEATGEEK_CLIENT_SECRET", "")

# In case SeatGeek requires a different scheme later (e.g. OAuth),
# you can switch this flag and centralize the change here.
SEATGEEK_AUTH_MODE = os.getenv("SEATGEEK_AUTH_MODE", "query")  # "query" | "none" | "header"


def _auth_params() -> Dict[str, str]:
    """
    Build authentication parameters for SeatGeek requests.
    Adjust this once you know the exact requirements.
    """
    if SEATGEEK_AUTH_MODE == "query":
        params: Dict[str, str] = {}
        if SEATGEEK_CLIENT_ID:
            params["client_id"] = SEATGEEK_CLIENT_ID
        if SEATGEEK_CLIENT_SECRET:
            params["client_secret"] = SEATGEEK_CLIENT_SECRET
        return params
    # Placeholder for future header-based auth, if needed.
    return {}


async def search_events(query: str, per_page: int = 5) -> List[Dict[str, Any]]:
    """
    Search SeatGeek events by free-text query.

    This is used to map CFP-style "Big 12 Championship" or
    "Texas Tech vs Oklahoma" into a concrete SeatGeek event.

    Returns a list of raw event dicts (no schema enforced here).
    """
    if not SEATGEEK_CLIENT_ID and SEATGEEK_AUTH_MODE == "query":
        # Not configured yet; fail soft so the API can respond with a clear message.
        return []

    base = SEATGEEK_BASE_URL.rstrip("/")
    url = f"{base}/events"
    params: Dict[str, Any] = {
        "q": query,
        "per_page": per_page,
    }
    params.update(_auth_params())

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    events = data.get("events") or data.get("results") or []
    # Normalize to a list
    if not isinstance(events, list):
        return []
    return events


async def get_event(event_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch a single SeatGeek event by ID.

    Once you have actual SeatGeek docs, you may want to adjust
    the endpoint path or how inventory is accessed.
    """
    if not SEATGEEK_CLIENT_ID and SEATGEEK_AUTH_MODE == "query":
        return None

    base = SEATGEEK_BASE_URL.rstrip("/")
    url = f"{base}/events/{event_id}"
    params = _auth_params()

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    # Some SeatGeek APIs wrap the event inside a top-level "event" field.
    if "event" in data and isinstance(data["event"], dict):
        return data["event"]
    return data
