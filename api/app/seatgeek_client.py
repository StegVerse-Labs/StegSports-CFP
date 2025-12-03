# api/app/seatgeek_client.py
#
# Light-weight SeatGeek integration for CFP StegSports.
# For now we only build search URLs with an affiliate code.

from __future__ import annotations

import os
import urllib.parse
from typing import Optional


class SeatGeekClient:
    """
    Build SeatGeek affiliate search URLs.

    Later, once your developer account is approved, we can extend this with:
      - API-based event discovery
      - direct linking to specific listings
    without changing the rest of the backend.
    """

    def __init__(self) -> None:
        # Base web URL (not the API host)
        self.base_url = os.getenv("SEATGEEK_WEB_BASE", "https://seatgeek.com")
        # Your affiliate / partner code – whatever SeatGeek / Partnerize gives you.
        self.affiliate_code = os.getenv("SEATGEEK_AFFILIATE_CODE", "").strip()

    def build_search_url(
        self,
        event_name: str,
        location: Optional[str] = None,
        date: Optional[str] = None,
        group_size: int = 2,
    ) -> Optional[str]:
        """
        Build a SeatGeek search URL like:
          https://seatgeek.com/search?search=Texas%20Tech&aid=XYZ
        """
        if not event_name:
            return None

        query_parts = [event_name]
        if location:
            query_parts.append(location)
        if date:
            query_parts.append(date)

        search_query = " ".join(query_parts)

        params = {
            "search": search_query,
            # We'll pass group size as a hint; SeatGeek may ignore it but it's
            # useful for analytics on your side if they echo it back.
            "group_size": str(group_size),
        }

        if self.affiliate_code:
            # Many networks use "aid" or "partner" – tweak once you know the final param
            params["aid"] = self.affiliate_code

        return f"{self.base_url}/search?{urllib.parse.urlencode(params)}"
