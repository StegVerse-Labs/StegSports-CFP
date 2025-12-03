# api/app/main.py
# [CFP-API-MAIN v2025-12-03-01]

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes_tickets import router as tickets_router
from .routes_partnerize import router as partnerize_router

app = FastAPI(
    title="StegSports CFP API",
    version="0.2.0",
    description=(
        "Backend API for CFP.StegSports.app\n\n"
        "- Tickets search & outbound links (SeatGeek / StubHub / others)\n"
        "- Affiliate / Partner tracking via Partnerize\n"
        "- Health / diagnostics endpoints"
    ),
)

# -------------------------------------------------------------------------
# CORS – allow the CFP front-end (and localhost for testing) to call the API
# -------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],            # tighten later if you want
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------------------
# Basic health + root
# -------------------------------------------------------------------------


@app.get("/", tags=["meta"])
async def root() -> dict:
    return {
        "service": "stegsports-cfp-api",
        "status": "ok",
        "docs": "/docs",
        "healthz": "/healthz",
    }


@app.get("/healthz", tags=["meta"])
async def healthz() -> dict:
    return {"status": "ok"}


# -------------------------------------------------------------------------
# Routers
# -------------------------------------------------------------------------

# Tickets: SeatGeek / StubHub, search helpers, etc.
app.include_router(
    tickets_router,
    prefix="/v1/tickets",
)

# Partnerize: affiliate reporting, conversions, etc.
app.include_router(
    partnerize_router,
    prefix="/v1/partnerize",
)
