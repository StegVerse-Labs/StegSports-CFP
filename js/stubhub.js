// [SCFP-STUBHUB v1.1]
// Mirrors the SeatGeek helper: simple, clean, stable.
// Replace STUBHUB_AFFILIATE_ID with your real StubHub affiliate/campaign parameter.

const StegStubHub = (function () {
  // TODO: Replace this with your real StubHub affiliate ID / campaign key:
  const AFFILIATE_ID = "YOUR_STUBHUB_AFFILIATE_ID";

  /**
   * Generic search-based StubHub affiliate link.
   * Works identically to StegSeatGeek.buildSearchUrl.
   *
   * StubHub does not always use fully stable event slugs externally.
   * Search-based linking is the safest, highest-success-rate entry point.
   */
  function buildSearchUrl(query) {
    const base = "https://www.stubhub.com/find/";
    const params = new URLSearchParams();

    // Query term
    params.set("q", query);

    // Affiliate attribution
    if (AFFILIATE_ID) {
      // StubHub’s typical tracking variable is “aid” or “campaign” depending on program.
      // Keeping “aid” here so your system remains parallel with SeatGeek.
      params.set("aid", AFFILIATE_ID);
    }

    return `${base}?${params.toString()}`;
  }

  /**
   * Wrapper for future direct-event linking.
   * Matches structure of StegSeatGeek.buildEventUrl.
   */
  function buildEventUrl(slugOrQuery) {
    // For now identical to search:
    return buildSearchUrl(slugOrQuery);
  }

  return {
    buildSearchUrl,
    buildEventUrl
  };
})();
