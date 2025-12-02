# routes_tickets.py
# v2025-12-02-01 — Unified ticket search (SeatGeek + StubHub)
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, validator

from . import seatgeek_client, stubhub_client

router = APIRouter(prefix="/v1/tickets", tags=["tickets"])


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class TicketSource(str, Enum):
    seatgeek = "seatgeek"
    stubhub = "stubhub"
    mixed = "mixed"


class GroupingPrefs(BaseModel):
    """
    Group seating prefs — e.g. group_size=4, max_rows=2 means:
    "Try to find 4 seats that can be spread across at most two rows."
    """
    group_size: int = Field(ge=1, description="Total seats needed in the group.")
    max_rows: int = Field(
        ge=1,
        description="Max number of distinct rows allowed for this group.",
    )


class TicketSearchRequest(BaseModel):
    q: Optional[str] = Field(None, description="Search keyword (team, matchup, etc.)")
    city: Optional[str] = None
    state: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    radius_miles: Optional[int] = Field(
        None, description="Search radius when lat/lon are supplied."
    )
    source: TicketSource = Field(
        TicketSource.mixed,
        description="Where to pull results from (SeatGeek, StubHub, or both).",
    )
    ab_variant: Optional[str] = Field(
        None,
        description="Optional A/B variant label ('A' or 'B') for revenue testing.",
    )
    grouping: Optional[GroupingPrefs] = Field(
        None,
        description=(
            "Optional group seating preference. We *hint* providers and tag "
            "results that look compatible, but final layout depends on the "
            "ticketing platform."
        ),
    )
    limit: int = Field(20, ge=1, le=100)

    @validator("ab_variant")
    def _validate_ab(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        upper = v.upper()
        if upper not in {"A", "B"}:
            raise ValueError("ab_variant must be 'A' or 'B' if provided")
        return upper


class TicketOffer(BaseModel):
    provider: str
    id: str
    title: Optional[str]
    datetime_local: Optional[str]
    url: Optional[str]
    venue: Dict[str, Any]
    pricing: Dict[str, Any]
    # Simple tags for downstream A/B + grouping logic
    variant: Optional[str] = None
    grouping_score: Optional[float] = None


class TicketSearchResponse(BaseModel):
    source: TicketSource
    ab_variant: Optional[str]
    offers: List[TicketOffer]


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _score_grouping(event: Dict[str, Any], prefs: GroupingPrefs) -> float:
    """
    Very lightweight heuristic for "multi-row friendly" events.

    For now we don't have guaranteed seat-level detail from providers, so this
    just returns:
      - 1.0 if group_size == 1
      - 0.8 if group_size <= 4 and max_rows >= 2
      - 0.5 otherwise

    Once we have real seat metadata coming from StubHub or SeatGeek, we can
    upgrade this to look at actual row/section distributions.
    """
    if prefs.group_size <= 1:
        return 1.0
    if prefs.group_size <= 4 and prefs.max_rows >= 2:
        return 0.8
    return 0.5


def _decorate_offers(
    events: List[Dict[str, Any]],
    *,
    variant: Optional[str],
    grouping: Optional[GroupingPrefs],
) -> List[TicketOffer]:
    offers: List[TicketOffer] = []
    for e in events:
        grouping_score = None
        if grouping is not None:
            grouping_score = _score_grouping(e, grouping)

        offers.append(
            TicketOffer(
                provider=e.get("provider", "unknown"),
                id=str(e.get("id")),
                title=e.get("title"),
                datetime_local=e.get("datetime_local"),
                url=e.get("url"),
                venue=e.get("venue") or {},
                pricing=e.get("pricing") or {},
                variant=variant,
                grouping_score=grouping_score,
            )
        )
    return offers


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post("/search", response_model=TicketSearchResponse)
async def search_tickets(body: TicketSearchRequest) -> TicketSearchResponse:
    """
    Unified ticket search entrypoint for CFP.StegSports.app

    - Uses SeatGeek and/or StubHub depending on `source`
    - Supports A/B variants (SeatGeek-heavy vs StubHub-heavy)
    - Adds basic group-seating hints for multi-row groups
    """

    # Decide which providers to hit
    want_seatgeek = body.source in (TicketSource.seatgeek, TicketSource.mixed)
    want_stubhub = body.source in (TicketSource.stubhub, TicketSource.mixed)

    if not (want_seatgeek or want_stubhub):
        raise HTTPException(status_code=400, detail="No ticket providers selected")

    # In "mixed" mode, use ab_variant to bias the display order:
    #   - A: SeatGeek first
    #   - B: StubHub first
    variant = (body.ab_variant or "A").upper()
    if variant not in {"A", "B"}:
        variant = "A"

    # Kick off provider calls
    events_seatgeek: List[Dict[str, Any]] = []
    events_stubhub: List[Dict[str, Any]] = []

    if want_seatgeek:
        try:
            events_seatgeek = await seatgeek_client.search_events(
                query=body.q,
                city=body.city,
                state=body.state,
                lat=body.lat,
                lon=body.lon,
                radius_miles=body.radius_miles,
                per_page=body.limit,
            )
        except Exception as exc:  # noqa: BLE001
            # Don't take down the whole endpoint if one provider is unhappy
            raise HTTPException(
                status_code=502,
                detail=f"SeatGeek error: {exc}",
            ) from exc

    if want_stubhub:
        try:
            events_stubhub = await stubhub_client.search_events(
                query=body.q,
                city=body.city,
                state=body.state,
                lat=body.lat,
                lon=body.lon,
                radius_miles=body.radius_miles,
                per_page=body.limit,
            )
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=502,
                detail=f"StubHub error: {exc}",
            ) from exc

    # Decorate with A/B + grouping hints
    grouping = body.grouping
    offers_seatgeek = _decorate_offers(events_seatgeek, variant=variant, grouping=grouping)
    offers_stubhub = _decorate_offers(events_stubhub, variant=variant, grouping=grouping)

    # Simple A/B ordering:
    #  - Variant A: SeatGeek first, then StubHub
    #  - Variant B: StubHub first, then SeatGeek
    if body.source == TicketSource.mixed:
        if variant == "A":
            offers = offers_seatgeek + offers_stubhub
        else:
            offers = offers_stubhub + offers_seatgeek
    elif body.source == TicketSource.seatgeek:
        offers = offers_seatgeek
    else:
        offers = offers_stubhub

    # Hard limit in case providers returned more than requested
    offers = offers[: body.limit]

    return TicketSearchResponse(
        source=body.source,
        ab_variant=variant,
        offers=offers,
    )


@router.get("/providers", response_model=List[str])
async def list_ticket_providers() -> List[str]:
    """
    Small helper for the front-end to know what providers are wired in.
    """
    return [s.value for s in TicketSource]
