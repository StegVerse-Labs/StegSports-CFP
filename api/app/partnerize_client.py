# api/app/partnerize_client.py
# [SCW-AFFILIATE-PARTNERIZE v2025-12-03-01]

import os
import base64
from typing import Any, Dict, Optional

import httpx
from fastapi import HTTPException


class PartnerizeConfig:
    """Configuration loader for Partnerize API credentials."""

    def __init__(self) -> None:
        self.base_url: str = os.getenv("PARTNERIZE_BASE_URL", "https://api.partnerize.com").rstrip("/")
        self.application_key: Optional[str] = os.getenv("PARTNERIZE_APPLICATION_KEY")
        self.user_api_key: Optional[str] = os.getenv("PARTNERIZE_USER_API_KEY")

        if not self.application_key or not self.user_api_key:
            # We raise 503 so the caller knows Partnerize is not yet configured,
            # but the rest of the SCW system can continue to operate.
            raise HTTPException(
                status_code=503,
                detail="Partnerize credentials are not configured (missing PARTNERIZE_APPLICATION_KEY or PARTNERIZE_USER_API_KEY).",
            )

    @property
    def auth_header(self) -> str:
        """
        Build the HTTP Basic Authorization header:

        Authorization: Basic base64(application_key:user_api_key)
        """
        token_bytes = f"{self.application_key}:{self.user_api_key}".encode("utf-8")
        encoded = base64.b64encode(token_bytes).decode("ascii")
        return f"Basic {encoded}"


async def partnerize_get(path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Generic GET helper for Partnerize API.

    - path: relative API path, e.g. "/network" or "/v3/brand/campaigns/{id}/conversions/bulk"
    - params: optional query parameters (offset, limit, date filters, etc.)
    """
    cfg = PartnerizeConfig()

    # normalise path
    if not path.startswith("/"):
        path = "/" + path

    url = cfg.base_url + path

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(
                url,
                headers={"Authorization": cfg.auth_header},
                params=params or {},
            )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Partnerize API request error: {exc}",
        ) from exc

    # Partnerize tends to return useful JSON even on non-200; we still treat 4xx/5xx as error.
    try:
        data = response.json()
    except ValueError:
        data = {"raw": response.text}

    if response.status_code >= 400:
        raise HTTPException(
            status_code=response.status_code,
            detail={
                "message": "Partnerize API returned an error",
                "status_code": response.status_code,
                "body": data,
            },
        )

    return data
