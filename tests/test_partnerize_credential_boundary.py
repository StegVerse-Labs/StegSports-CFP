from pathlib import Path

import pytest
from fastapi import HTTPException

from api.app import partnerize_client
from api.app import routes_partnerize


ROOT = Path(__file__).resolve().parents[1]
CLIENT = ROOT / "api" / "app" / "partnerize_client.py"
ROUTES = ROOT / "api" / "app" / "routes_partnerize.py"


@pytest.mark.asyncio
async def test_partnerize_client_fails_closed_to_tvc_route():
    with pytest.raises(HTTPException) as caught:
        await partnerize_client.get_networks()
    assert caught.value.status_code == 503
    assert "TVC_ADMITTED_PROVIDER_ROUTE_REQUIRED" in str(caught.value.detail)


@pytest.mark.asyncio
async def test_partnerize_route_provider_call_fails_closed():
    with pytest.raises(HTTPException) as caught:
        await routes_partnerize._get("/network")
    assert caught.value.status_code == 503
    assert "TVC_ADMITTED_PROVIDER_ROUTE_REQUIRED" in str(caught.value.detail)


def test_partnerize_source_has_no_consumer_provider_credentials_or_auth():
    text = CLIENT.read_text(encoding="utf-8") + "\n" + ROUTES.read_text(encoding="utf-8")
    for marker in (
        "PARTNERIZE_APP_KEY",
        "PARTNERIZE_API_KEY",
        "PARTNERIZE_USER_API_KEY",
        "Authorization\": f\"Basic",
        "base64.b64encode",
        "httpx.AsyncClient",
        "api.partnerize.com",
    ):
        assert marker not in text
