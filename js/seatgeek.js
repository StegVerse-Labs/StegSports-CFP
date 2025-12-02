// [SCFP-SEATGEEK v1]
//
// Simple helper for constructing SeatGeek affiliate links.
// Replace SEATGEEK_AFFILIATE_ID with your real affiliate ID from their program.

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
    // If you later know exact event slugs, you can switch to /events/<slug>
    return buildSearchUrl(slugOrQuery);
  }

  return {
    buildSearchUrl,
    buildEventUrl
  };
})();
