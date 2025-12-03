# api/app/routes_tickets.py
#
# Ticket search endpoints with simple A/B split between SeatGeek
# and StubHub, plus support fields for group-size / multi-row seating.

from __future__ import annotations

import hashlib
import os
from enum import Enum
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .seatgeek_client import SeatGeekClient
from .stubhub_client import StubHubClient

router = APIRouter()

# -------------------------------------------------------------------
# Models
# -------------------------------------------------------------------


class Provider(str, Enum):
    seatgeek = "seatGeek"
    stubhub = "stubHub"
    auto = "auto"  # let backend choose (A/B)


class AffiliateLink(BaseModel):
    provider: Provider = Field(..., description="Ticket provider")
    label: str = Field(..., description="CTA label to show on the button")
    url: str = Field(..., description="Affiliate / search URL")
    experiment_bucket: Optional[str] = Field(
        None, description="A/B bucket id (e.g. seatGeek or stubHub)"
    )


class TicketSearchResponse(BaseModel):
    provider: Provider
    experiment_bucket: str
    group_size: int = Field(..., ge=1)
    max_rows: int = Field(..., ge=1)
    event_name: str
    location: Optional[str] = None
    date: Optional[str] = None
    links: List[AffiliateLink]


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------


def _choose_provider(user_choice: Provider, experiment_id: Optional[str]) -> Provider:
    """
    Decide which provider to use when provider=auto.
    Stable hashing so the same experiment_id stays in the same bucket.
    """
    if user_choice != Provider.auto:
        return user_choice

    # Allow overriding with env var if you want to force a side
    forced = os.getenv("CFP_DEFAULT_PROVIDER", "").strip().lower()
    if forced == "seatgeek":
        return Provider.seatgeek
    if forced == "stubhub":
        return Provider.stubhub

    if not experiment_id:
        # No experiment id – default to SeatGeek for now.
        return Provider.seatgeek

    digest = hashlib.sha256(experiment_id.encode("utf-8")).hexdigest()
    bucket = int(digest[:4], 16)  # small, but stable
    return Provider.seatgeek if bucket % 2 == 0 else Provider.stubhub


# -------------------------------------------------------------------
# Endpoint
# -------------------------------------------------------------------


@router.get("/search", response_model=TicketSearchResponse)
async def search_tickets(
    event_name: str = Query(..., description="Game / matchup or team name"),
    location: Optional[str] = Query(
        None, description="City / stadium / generic location text"
    ),
    date: Optional[str] = Query(
        None, description="Optional date string for the event (free text)"
    ),
    provider: Provider = Query(
        Provider.auto,
        description="seatGeek, stubHub, or auto (let backend A/B decide)",
    ),
    group_size: int = Query(
        2,
        ge=1,
        description="Number of people in the group (for display & analytics).",
    ),
    max_rows: int = Query(
        1,
        ge=1,
        description=(
            "Maximum acceptable rows to split the group over. "
            "E.g. group_size=4, max_rows=2 -> okay with 2+2 on back-to-back rows."
        ),
    ),
    experiment_id: Optional[str] = Query(
        None,
        description=(
            "Opaque id used for A/B bucketing (cookie, session id, IP hash, etc.)."
        ),
    ),
) -> TicketSearchResponse:
    """
    Build affiliate search links for the requested event.

    NOTE: While SeatGeek / StubHub APIs are pending / limited, this operates in
    'link-builder' mode – we construct deep links to provider search pages with
    your affiliate codes. Later we can upgrade to full inventory queries.
    """
    chosen = _choose_provider(provider, experiment_id)

    seatgeek = SeatGeekClient()
    stubhub = StubHubClient()

    links: List[AffiliateLink] = []

    # Always generate both links so the frontend can show alternatives,
    # but flag which one is the "primary" for this user.
    sg_url = seatgeek.build_search_url(
        event_name=event_name, location=location, date=date, group_size=group_size
    )
    if sg_url:
        links.append(
            AffiliateLink(
                provider=Provider.seatgeek,
                label="View tickets on SeatGeek",
                url=sg_url,
                experiment_bucket="primary"
                if chosen == Provider.seatgeek
                else "secondary",
            )
        )

    sh_url = stubhub.build_search_url(
        event_name=event_name, location=location, date=date, group_size=group_size
    )
    if sh_url:
        links.append(
            AffiliateLink(
                provider=Provider.stubhub,
                label="View tickets on StubHub",
                url=sh_url,
                experiment_bucket="primary"
                if chosen == Provider.stubhub
                else "secondary",
            )
        )

    if not links:
        raise HTTPException(
            status_code=500,
            detail="No affiliate providers are configured yet. "
            "Check SeatGeek/StubHub environment variables.",
        )

    # Use a simple string so the frontend can log / inspect.
    bucket = "seatGeek" if chosen == Provider.seatgeek else "stubHub"

    return TicketSearchResponse(
        provider=chosen,
        experiment_bucket=bucket,
        group_size=group_size,
        max_rows=max_rows,
        event_name=event_name,
        location=location,
        date=date,
        links=links,
    )
