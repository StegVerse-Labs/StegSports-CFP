// [SCFP-STUBHUB v1.1]
// Mirrors the SeatGeek helper: simple, clean, stable.
// Replace STUBHUB_AFFILIATE_ID with your real StubHub affiliate/campaign parameter.

const StegStubHub = (function () {
  // TODO: Replace this with your real StubHub affiliate ID / campaign key:
  const AFFILIATE_ID = "YOUR_STUBHUB_AFFILIATE_ID";

  /**
   * Generic search-based StubHub affiliate link.
   * Works similarly to StegSeatGeek.buildSearchUrl.
   */
  function buildSearchUrl(query) {
    const base = "https://www.stubhub.com/find/";
    const params = new URLSearchParams();

    params.set("q", query);

    // Affiliate tracking; param name can be adjusted once StubHub confirms.
    if (AFFILIATE_ID) {
      params.set("aid", AFFILIATE_ID);
    }

    return `${base}?${params.toString()}`;
  }

  /**
   * Wrapper for potential direct-event linking later.
   */
  function buildEventUrl(slugOrQuery) {
    return buildSearchUrl(slugOrQuery);
  }

  return {
    buildSearchUrl,
    buildEventUrl
  };
})();
