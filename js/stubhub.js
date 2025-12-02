// [SCFP-STUBHUB v1.2]
// Mirrors the SeatGeek helper but with optional group/rows/stacks metadata.
// Replace STUBHUB_AFFILIATE_ID with your real StubHub affiliate/campaign parameter.

const StegStubHub = (function () {
  // TODO: Replace this with your real StubHub affiliate ID / campaign key:
  const AFFILIATE_ID = "YOUR_STUBHUB_AFFILIATE_ID";

  /**
   * Generic search-based StubHub affiliate link.
   * Optional `opts` carries group & seating preferences:
   *   - opts.groupSize : number
   *   - opts.maxRows   : 1 | 2 | 3 | string
   *   - opts.stacked   : boolean
   *
   * We do two things:
   *   1) Enrich the search text with human-readable hints
   *   2) Append machine-readable query params (sg_group, sg_rows, sg_stacked)
   *      so SCW / StegSports can analyze patterns later.
   */
  function buildSearchUrl(query, opts) {
    const base = "https://www.stubhub.com/find/";
    const options = opts || {};

    let q = String(query || "").trim();
    const hintParts = [];

    if (options.groupSize && Number(options.groupSize) > 0) {
      hintParts.push(`${options.groupSize} tickets`);
    }
    if (options.maxRows) {
      const r = String(options.maxRows);
      if (r === "1") {
        hintParts.push("same row only");
      } else {
        hintParts.push(`up to ${r} rows`);
      }
    }
    if (options.stacked) {
      hintParts.push("stacked rows ok");
    }

    if (hintParts.length > 0) {
      // Append hints to the base query in a natural way.
      q = q + " " + hintParts.join(", ");
    }

    const params = new URLSearchParams();
    if (q) {
      params.set("q", q);
    }

    // Affiliate tracking; param name can be adjusted once StubHub confirms.
    if (AFFILIATE_ID) {
      params.set("aid", AFFILIATE_ID);
    }

    // Machine-readable hints for StegSports / SCW intelligence.
    if (options.groupSize) {
      params.set("sg_group", String(options.groupSize));
    }
    if (options.maxRows) {
      params.set("sg_rows", String(options.maxRows));
    }
    if (options.stacked) {
      params.set("sg_stacked", "1");
    }

    return `${base}?${params.toString()}`;
  }

  /**
   * Wrapper for potential direct-event linking later.
   * Kept compatible with SeatGeek's buildEventUrl.
   */
  function buildEventUrl(slugOrQuery) {
    return buildSearchUrl(slugOrQuery);
  }

  return {
    buildSearchUrl,
    buildEventUrl
  };
})();
