# api/app/stubhub_client.py
#
# Light-weight StubHub integration for CFP StegSports.
# For now we mirror SeatGeek: build an affiliate search URL.
# Later we can plug in the OAuth flows you pasted once credentials are ready.

from __future__ import annotations

import os
import urllib.parse
from typing import Optional


class StubHubClient:
    def __init__(self) -> None:
        # Public web site, not the API host
        self.base_url = os.getenv("STUBHUB_WEB_BASE", "https://www.stubhub.com")
        self.affiliate_code = os.getenv("STUBHUB_AFFILIATE_CODE", "").strip()

    def build_search_url(
        self,
        event_name: str,
        location: Optional[str] = None,
        date: Optional[str] = None,
        group_size: int = 2,
    ) -> Optional[str]:
        """
        Construct a generic StubHub search URL.

        Exact URL shape may change once you get their official affiliate
        template; this gives us a single place to update when that happens.
        """
        if not event_name:
            return None

        query_parts = [event_name]
        if location:
            query_parts.append(location)
        if date:
            query_parts.append(date)

        keyword = " ".join(query_parts)

        params = {
            "q": keyword,
            "group_size": str(group_size),
        }

        if self.affiliate_code:
            # Placeholder param name for partner tracking – adjust once confirmed.
            params["partner_id"] = self.affiliate_code

        # A very broad search endpoint – stable enough to start with
        return f"{self.base_url}/s/?{urllib.parse.urlencode(params)}"
