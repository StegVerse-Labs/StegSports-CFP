from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .seatgeek_client import search_events

router = APIRouter()


# ---------------------------------------------------------
# Models
# ---------------------------------------------------------
class TicketPlanRequest(BaseModel):
    provider: str = Field("seatgeek", description="Ticket provider; currently only 'seatgeek' is supported.")
    event_query: str = Field(..., min_length=3, description="Free-text event search (e.g. 'Big 12 Championship Texas Tech').")
    group_size: int = Field(..., ge=1, le=20, description="Total number of tickets needed.")
    max_rows: Optional[int] = Field(
        None,
        ge=1,
        le=5,
        description="Maximum number of rows your group is willing to span (1 = same row only).",
    )
    stacked_ok: bool = Field(
        False,
        description="If true, allows front/back stacked rows (e.g. Row 10 + Row 11) instead of strictly same-row seating.",
    )
    max_price: Optional[float] = Field(
        None,
        gt=0,
        description="Optional price cap per ticket (in event currency).",
    )


class SeatBlock(BaseModel):
    section: str
    rows: List[str]
    total_tickets: int
    price_per_ticket: float
    approx_seats: str
    source: str = "demo"


class TicketPlanResponse(BaseModel):
    ok: bool
    provider: str
    strategy: str
    event_candidates: List[Dict[str, Any]]
    best_options: List[SeatBlock]
    note: str


# ---------------------------------------------------------
# Internal demo inventory + grouping logic
#
# This is intentionally using a synthetic inventory so we
# can demo the grouping algorithm *before* we plug in real
# SeatGeek listings. Later, you just swap build_demo_inventory()
# with real data from SeatGeek get_event/listings calls.
# ---------------------------------------------------------
def build_demo_inventory() -> List[Dict[str, Any]]:
    """
    Synthetic inventory representing a typical lower-bowl cluster at a CFP or
    conference championship game. This is used for now to exercise the grouping
    algorithm while we wait for SeatGeek listing docs / access.

    Each item:
      - section: string label
      - row: string label
      - start: first seat number (inclusive)
      - end: last seat number (inclusive)
      - price: price per ticket
    """
    demo = [
        {"section": "112", "row": "10", "start": 5, "end": 12, "price": 210.0},
        {"section": "112", "row": "11", "start": 5, "end": 10, "price": 205.0},
        {"section": "112", "row": "12", "start": 6, "end": 11, "price": 195.0},
        {"section": "113", "row": "9", "start": 1, "end": 6, "price": 185.0},
        {"section": "113", "row": "10", "start": 1, "end": 4, "price": 175.0},
    ]
    return demo


def _block_capacity(item: Dict[str, Any]) -> int:
    return int(item["end"]) - int(item["start"]) + 1


def _block_overlap(a: Dict[str, Any], b: Dict[str, Any]) -> int:
    """
    Seat overlap between two blocks in the same section.
    """
    if a["section"] != b["section"]:
        return 0
    start = max(a["start"], b["start"])
    end = min(a["end"], b["end"])
    return max(0, end - start + 1)


def compute_grouping(
    inventory: List[Dict[str, Any]],
    group_size: int,
    max_rows: Optional[int],
    stacked_ok: bool,
    max_price: Optional[float],
) -> List[SeatBlock]:
    """
    Very small, readable grouping heuristic:

    1. Try to find a single block that fits the whole group in one row.
    2. If not found and max_rows >= 2, look for two rows in same section with
       overlapping seats that together meet group_size.
    3. If still not found and max_rows >= 3 and stacked_ok, consider 3-row combos.
    """
    if not inventory:
        return []

    effective_max_rows = max_rows or 3

    # Filter by price cap if present
    if max_price is not None:
        inv = [i for i in inventory if i["price"] <= max_price]
    else:
        inv = list(inventory)

    if not inv:
        return []

    options: List[SeatBlock] = []

    # 1) Single-row blocks
    for item in inv:
        cap = _block_capacity(item)
        if cap >= group_size:
            approx = f"Seats {item['start']}-{item['start'] + group_size - 1}"
            options.append(
                SeatBlock(
                    section=item["section"],
                    rows=[item["row"]],
                    total_tickets=group_size,
                    price_per_ticket=float(item["price"]),
                    approx_seats=approx,
                    source="demo_single",
                )
            )

    if options:
        # Sort by price asc
        options.sort(key=lambda b: b.price_per_ticket)
        return options[:5]

    # 2) Two-row combos
    if effective_max_rows >= 2:
        for i in range(len(inv)):
            a = inv[i]
            for j in range(i + 1, len(inv)):
                b = inv[j]
                if a["section"] != b["section"]:
                    continue
                overlap = _block_overlap(a, b)
                if overlap <= 0:
                    continue
                cap = _block_capacity(a) + _block_capacity(b)
                if cap < group_size:
                    continue
                avg_price = (a["price"] + b["price"]) / 2.0
                approx = f"Rows {a['row']}/{b['row']} seats ~{a['start']}-{a['start'] + group_size // 2}"
                options.append(
                    SeatBlock(
                        section=a["section"],
                        rows=[a["row"], b["row"]],
                        total_tickets=group_size,
                        price_per_ticket=float(avg_price),
                        approx_seats=approx,
                        source="demo_two_row",
                    )
                )

    if options:
        options.sort(key=lambda b: b.price_per_ticket)
        return options[:5]

    # 3) Three-row combos (if allowed and stacked_ok)
    if effective_max_rows >= 3 and stacked_ok:
        for i in range(len(inv)):
            a = inv[i]
            for j in range(i + 1, len(inv)):
                b = inv[j]
                if a["section"] != b["section"]:
                    continue
                for k in range(j + 1, len(inv)):
                    c = inv[k]
                    if c["section"] != a["section"]:
                        continue
                    cap = _block_capacity(a) + _block_capacity(b) + _block_capacity(c)
                    if cap < group_size:
                        continue
                    avg_price = (a["price"] + b["price"] + c["price"]) / 3.0
                    approx = f"Rows {a['row']}/{b['row']}/{c['row']} cluster"
                    options.append(
                        SeatBlock(
                            section=a["section"],
                            rows=[a["row"], b["row"], c["row"]],
                            total_tickets=group_size,
                            price_per_ticket=float(avg_price),
                            approx_seats=approx,
                            source="demo_three_row",
                        )
                    )

    if options:
        options.sort(key=lambda b: b.price_per_ticket)
        return options[:5]

    return []


# ---------------------------------------------------------
# API route
# ---------------------------------------------------------
@router.post("/plan", response_model=TicketPlanResponse)
async def plan_tickets(req: TicketPlanRequest) -> TicketPlanResponse:
    """
    High-level "smart group seating" endpoint (SeatGeek-first design).

    For now:
      - Uses SeatGeek event search to surface candidate events.
      - Uses a synthetic demo inventory to demonstrate grouping logic.
    Later:
      - Replace build_demo_inventory() with real SeatGeek listings
        for the chosen event.
    """
    provider = (req.provider or "seatgeek").lower()
    if provider != "seatgeek":
        raise HTTPException(status_code=400, detail="Only 'seatgeek' provider is supported at this time.")

    # 1) Discover events matching the query
    events = await search_events(req.event_query, per_page=5)
    if not events:
        raise HTTPException(status_code=404, detail="No events found for this query via SeatGeek.")

    # For now we just expose a tiny subset of fields for the response.
    candidates: List[Dict[str, Any]] = []
    for ev in events:
        candidates.append(
            {
                "id": ev.get("id"),
                "title": ev.get("title") or ev.get("short_title"),
                "datetime_local": ev.get("datetime_local") or ev.get("datetime_utc"),
                "venue": (ev.get("venue", {}) or {}).get("name"),
                "display_location": (ev.get("venue", {}) or {}).get("display_location"),
                "score": ev.get("score"),
            }
        )

    # 2) Run grouping logic on demo inventory
    inventory = build_demo_inventory()
    best_options = compute_grouping(
        inventory=inventory,
        group_size=req.group_size,
        max_rows=req.max_rows,
        stacked_ok=req.stacked_ok,
        max_price=req.max_price,
    )

    # If we somehow have SeatGeek but no options from demo inventory,
    # we still respond with the event candidates.
    note = (
        "Using synthetic demo inventory only. "
        "Once SeatGeek listing APIs are wired, this endpoint will compute real seat groupings."
    )

    return TicketPlanResponse(
        ok=True,
        provider="seatgeek",
        strategy="group_size/max_rows/stacked_demo_v1",
        event_candidates=candidates,
        best_options=best_options,
        note=note,
    )
