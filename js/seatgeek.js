// [SCFP-SEATGEEK v1]
// Simple helper for constructing SeatGeek affiliate links.
// Replace SEATGEEK_AFFILIATE_ID with your real affiliate ID.

const StegSeatGeek = (function () {
  const AFFILIATE_ID = "YOUR_SEATGEEK_AFFILIATE_ID"; // TODO: set real value

  function buildSearchUrl(query) {
    const base = "https://seatgeek.com/search";
    const params = new URLSearchParams();
    params.set("search", query);
    if (AFFILIATE_ID) {
      params.set("aid", AFFILIATE_ID);
    }
    return `${base}?${params.toString()}`;
  }

  function buildEventUrl(slugOrQuery) {
    // For now, just treat slugOrQuery as a search term.
    return buildSearchUrl(slugOrQuery);
  }

  return {
    buildSearchUrl,
    buildEventUrl
  };
})();
