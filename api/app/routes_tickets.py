# api/app/routes_tickets.py
# [CFP-TICKETS-ROUTES v2025-12-03-02]

import os
import time
import random
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse

from urllib.parse import urlencode

router = APIRouter(tags=["tickets"])

# -------------------------------------------------------------------
# Config / Env
# -------------------------------------------------------------------

SEATGEEK_BASE = os.getenv("SEATGEEK_SEARCH_BASE", "https://seatgeek.com/search")
STUBHUB_BASE = os.getenv("STUBHUB_SEARCH_BASE", "https://www.stubhub.com/s/")

# These are *generic* affiliate tags; you can adjust param names later
SEATGEEK_AFFILIATE_TAG = os.getenv("SEATGEEK_AFFILIATE_TAG", "")
STUBHUB_AFFILIATE_TAG = os.getenv("STUBHUB_AFFILIATE_TAG", "")

# Split test config: percentage of traffic that gets SeatGeek as *primary*
SPLIT_SEATGEEK_PERCENT = int(os.getenv("SPLIT_TEST_SEATGEEK_PERCENT", "50"))

# Mode: "auto" | "seatGeek" | "stubHub"
PRIMARY_MODE = os.getenv("CFP_PRIMARY_MODE", "auto").lower()

# In-memory click log (rotating)
_MAX_CLICKS = 500
_CLICK_LOG: List[Dict[str, Any]] = []


def _log_click(entry: Dict[str, Any]) -> None:
    entry["ts"] = int(time.time())
    _CLICK_LOG.insert(0, entry)
    if len(_CLICK_LOG) > _MAX_CLICKS:
        del _CLICK_LOG[_MAX_CLICKS:]


# -------------------------------------------------------------------
# URL builders
# -------------------------------------------------------------------


def _build_seatgeek_url(
    event_name: str,
    group_size: Optional[int],
    max_rows: Optional[int],
) -> str:
    params: Dict[str, Any] = {
        "search": event_name,
    }
    if group_size is not None:
        params["group_size"] = group_size
    if max_rows is not None:
        params["max_rows"] = max_rows

    if SEATGEEK_AFFILIATE_TAG:
        # You can swap "aid" for the official param SeatGeek gives you.
        params["aid"] = SEATGEEK_AFFILIATE_TAG

    return f"{SEATGEEK_BASE.rstrip('/')}?{urlencode(params)}"


def _build_stubhub_url(
    event_name: str,
    group_size: Optional[int],
    max_rows: Optional[int],
) -> str:
    params: Dict[str, Any] = {
        "q": event_name,
    }
    if group_size is not None:
        params["group_size"] = group_size
    if max_rows is not None:
        params["max_rows"] = max_rows

    if STUBHUB_AFFILIATE_TAG:
        # Again: "aid" is a placeholder; adjust once StubHub confirms the param.
        params["aid"] = STUBHUB_AFFILIATE_TAG

    return f"{STUBHUB_BASE.rstrip('/')}?{urlencode(params)}"


def _choose_primary_bucket() -> str:
    """
    Decide which provider is 'primary' for this request.
    """
    if PRIMARY_MODE == "seatgeek":
        return "seatGeek"
    if PRIMARY_MODE == "stubhub":
        return "stubHub"

    # auto / default: simple percentage-based split
    roll = random.randint(1, 100)
    return "seatGeek" if roll <= SPLIT_SEATGEEK_PERCENT else "stubHub"


# -------------------------------------------------------------------
# Search endpoint – returns metadata + provider URLs
# -------------------------------------------------------------------


@router.get("/search", summary="Ticket search helper with A/B provider split")
async def tickets_search(
    event_name: str = Query(..., description="Plain text event name, e.g. 'Texas Tech vs BYU'"),
    group_size: Optional[int] = Query(
        None,
        ge=1,
        description="Party size (optional). Used only to annotate URLs.",
    ),
    max_rows: Optional[int] = Query(
        None,
        ge=1,
        le=4,
        description=(
            "Max adjacent seat rows your group is okay with (1 = all same row, "
            "2 = OK with two stacked rows, etc.)."
        ),
    ),
) -> Dict[str, Any]:
    """
    This does NOT call SeatGeek / StubHub APIs yet. It simply constructs search URLs and
    chooses which provider is 'primary' for this request, so the UI can highlight it.
    """
    if not event_name.strip():
        raise HTTPException(status_code=400, detail="event_name is required")

    primary = _choose_primary_bucket()

    sg_url = _build_seatgeek_url(event_name, group_size, max_rows)
    sh_url = _build_stubhub_url(event_name, group_size, max_rows)

    # Relative click URLs – front-end will prepend its API base
    sg_click = "/v1/tickets/click?provider=seatGeek&" + urlencode(
        {
            "event_name": event_name,
            "group_size": group_size or "",
            "max_rows": max_rows or "",
            "bucket": primary if primary == "seatGeek" else "secondary",
        }
    )
    sh_click = "/v1/tickets/click?provider=stubHub&" + urlencode(
        {
            "event_name": event_name,
            "group_size": group_size or "",
            "max_rows": max_rows or "",
            "bucket": primary if primary == "stubHub" else "secondary",
        }
    )

    return {
        "ok": True,
        "event_name": event_name,
        "group_size": group_size,
        "max_rows": max_rows,
        "primary_provider": primary,
        "split": {
            "mode": PRIMARY_MODE,
            "seatGeek_percent": SPLIT_SEATGEEK_PERCENT,
        },
        "links": [
            {
                "provider": "seatGeek",
                "label": "View tickets on SeatGeek",
                "direct_url": sg_url,
                "click_url": sg_click,
                "role": "primary" if primary == "seatGeek" else "secondary",
            },
            {
                "provider": "stubHub",
                "label": "View tickets on StubHub",
                "direct_url": sh_url,
                "click_url": sh_click,
                "role": "primary" if primary == "stubHub" else "secondary",
            },
        ],
    }


# -------------------------------------------------------------------
# Click redirect endpoint – logs + redirects to provider
# -------------------------------------------------------------------


@router.get("/click", summary="Redirect to provider with logging")
async def tickets_click(
    request: Request,
    provider: str = Query(..., description="'seatGeek' or 'stubHub'"),
    event_name: str = Query(..., description="Event label used to build provider URL"),
    group_size: Optional[int] = Query(None, ge=1),
    max_rows: Optional[int] = Query(None, ge=1, le=4),
    bucket: Optional[str] = Query(
        None,
        description="Experiment bucket label, e.g. 'seatGeek', 'stubHub', 'secondary'",
    ),
):
    provider_norm = provider.strip()
    if provider_norm not in ("seatGeek", "stubHub"):
        raise HTTPException(status_code=400, detail="provider must be 'seatGeek' or 'stubHub'")

    if provider_norm == "seatGeek":
        dest = _build_seatgeek_url(event_name, group_size, max_rows)
    else:
        dest = _build_stubhub_url(event_name, group_size, max_rows)

    # Log the click
    client_ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent", "")

    _log_click(
        {
            "provider": provider_norm,
            "event_name": event_name,
            "group_size": group_size,
            "max_rows": max_rows,
            "bucket": bucket,
            "ip": client_ip,
            "user_agent": ua[:300],
        }
    )

    # 307 preserves method & body (not that we have one here) and is nicer for redirects from forms.
    return RedirectResponse(dest, status_code=307)


# -------------------------------------------------------------------
# Debug: recent clicks
# -------------------------------------------------------------------


@router.get("/clicks/recent", summary="Recent ticket clicks (debug only)")
async def recent_clicks(limit: int = Query(50, ge=1, le=200)) -> Dict[str, Any]:
    """
    Returns the most recent click events from this process memory.
    This is primarily for debugging / dashboards in early stages.
    """
    return {
        "ok": True,
        "limit": limit,
        "items": _CLICK_LOG[:limit],
    }
