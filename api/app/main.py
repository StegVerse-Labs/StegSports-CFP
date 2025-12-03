# api/app/main.py
#
# CFP StegSports backend
# Minimal FastAPI app that exposes ticket search endpoints
# and a simple health check for Render.

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes_tickets import router as tickets_router

app = FastAPI(
    title="CFP StegSports API",
    version="0.1.0",
    description="Ticket affiliate helper for CFP.StegSports.app",
)

# CORS – front-end may be on a different domain (Netlify/Vercel/etc)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later if you want
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz", tags=["internal"])
async def healthz() -> dict:
    """Render health check."""
    return {"status": "ok"}


# Tickets router (SeatGeek / StubHub, etc.)
app.include_router(tickets_router, prefix="/api/tickets", tags=["tickets"])
