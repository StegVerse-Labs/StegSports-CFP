// js/dashboard.js
// [CFP-AFFILIATE-DASHBOARD v2025-12-03-01]

// If you want to override this in HTML, set window.CFP_API_BASE before this script.
const API_BASE =
  (typeof window !== "undefined" && window.CFP_API_BASE) ||
  "https://scw-api.onrender.com"; // <-- update if your CFP API uses a different host

// Default Partnerize campaign ID for CFP traffic (placeholder)
const DEFAULT_CAMPAIGN_ID =
  (typeof window !== "undefined" && window.CFP_DEFAULT_CAMPAIGN_ID) || "";

// -------------------------
// Small utilities
// -------------------------

async function fetchJSON(path, params = {}) {
  const url = new URL(API_BASE + path);

  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      url.searchParams.set(key, String(value));
    }
  });

  const res = await fetch(url.toString(), {
    method: "GET",
    headers: {
      Accept: "application/json",
    },
  });

  if (!res.ok) {
    let bodyText = await res.text();
    let detail = bodyText;
    try {
      const json = JSON.parse(bodyText);
      detail = json.detail || bodyText;
    } catch (_) {
      // leave detail as text
    }
    throw new Error(`HTTP ${res.status}: ${detail}`);
  }

  return res.json();
}

function $(id) {
  return document.getElementById(id);
}

function formatMoney(value) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "–";
  }
  return `$${value.toFixed(2)}`;
}

// -------------------------
// Metrics computation
// -------------------------

function computeMetricsFromConversions(payload) {
  // Partnerize v3 bulk conversions shape is flexible; we try a few common patterns.
  let conversionsArray = [];

  if (Array.isArray(payload)) {
    conversionsArray = payload;
  } else if (Array.isArray(payload.conversions)) {
    conversionsArray = payload.conversions;
  } else if (Array.isArray(payload.items)) {
    conversionsArray = payload.items;
  }

  const totalConversions = conversionsArray.length;

  // Try to sum commission and sale values with a few common field names.
  let totalCommission = 0;
  let commissionCount = 0;

  for (const item of conversionsArray) {
    const cands = [
      item.commission_amount,
      item.commission,
      item.commission_value,
      item.commissionValue,
    ];

    const value = cands.find(
      (v) => typeof v === "number" || (typeof v === "string" && v.trim() !== "")
    );

    if (value !== undefined) {
      const num = typeof value === "number" ? value : parseFloat(value);
      if (!Number.isNaN(num)) {
        totalCommission += num;
        commissionCount += 1;
      }
    }
  }

  const avgCommission =
    commissionCount > 0 ? totalCommission / commissionCount : null;

  return {
    totalConversions,
    totalCommission: commissionCount > 0 ? totalCommission : null,
    avgCommission,
  };
}

// -------------------------
// DOM wiring
// -------------------------

async function loadNetworks() {
  const elRaw = $("networks-json");
  const elCount = $("metric-networks-count");
  const elNote = $("metric-networks-note");

  try {
    const data = await fetchJSON("/v1/partnerize/networks");
    elRaw.textContent = JSON.stringify(data, null, 2);

    let networksArray = [];
    if (Array.isArray(data.networks)) {
      networksArray = data.networks;
    } else if (Array.isArray(data.items)) {
      networksArray = data.items;
    }

    elCount.textContent = networksArray.length || "0";
    elNote.textContent =
      networksArray.length > 0
        ? "Connected via Partnerize"
        : "No networks found for current credentials.";
  } catch (err) {
    elRaw.textContent = `Error loading networks: ${err.message}`;
    elCount.textContent = "–";
    elNote.textContent = "Check Partnerize keys on the API service.";
  }
}

async function loadConversionsFromForm(evt) {
  if (evt) evt.preventDefault();

  const campaignInput = $("campaign-id");
  const startDateInput = $("start-date");
  const endDateInput = $("end-date");
  const limitInput = $("limit");
  const offsetInput = $("offset");
  const errorBox = $("filters-error");
  const rawBox = $("raw-json");

  errorBox.hidden = true;
  errorBox.textContent = "";

  const campaignIdRaw = campaignInput.value.trim();
  if (!campaignIdRaw) {
    errorBox.hidden = false;
    errorBox.textContent = "Please enter a Partnerize campaign ID.";
    return;
  }

  const params = {
    offset: offsetInput.value || 0,
    limit: limitInput.value || 200,
  };

  if (startDateInput.value) params.start_date = startDateInput.value;
  if (endDateInput.value) params.end_date = endDateInput.value;

  rawBox.textContent = "Loading…";

  try {
    const data = await fetchJSON(
      `/v1/partnerize/campaigns/${encodeURIComponent(campaignIdRaw)}/conversions`,
      params
    );
    rawBox.textContent = JSON.stringify(data, null, 2);

    // Update metrics
    const metrics = computeMetricsFromConversions(data);

    $("metric-total-conversions").textContent =
      metrics.totalConversions != null ? String(metrics.totalConversions) : "0";

    $("metric-total-conversions-note").textContent =
      metrics.totalConversions > 0
        ? "Count is for the current page / filters."
        : "No conversions found for the selected filters.";

    $("metric-total-commission").textContent = formatMoney(
      metrics.totalCommission
    );

    $("metric-total-commission-note").textContent =
      metrics.totalCommission != null
        ? "Sum of commission values found in the payload."
        : "No commission fields detected in this payload.";

    $("metric-avg-commission").textContent = formatMoney(
      metrics.avgCommission
    );
  } catch (err) {
    rawBox.textContent = `Error loading conversions: ${err.message}`;
    $("metric-total-conversions").textContent = "–";
    $("metric-total-conversions-note").textContent =
      "Unable to load conversions.";

    $("metric-total-commission").textContent = "–";
    $("metric-total-commission-note").textContent = "";

    $("metric-avg-commission").textContent = "–";

    errorBox.hidden = false;
    errorBox.textContent = err.message;
  }
}

function resetFilters() {
  $("campaign-id").value = DEFAULT_CAMPAIGN_ID || "";
  $("start-date").value = "";
  $("end-date").value = "";
  $("limit").value = "200";
  $("offset").value = "0";

  $("filters-error").hidden = true;
  $("filters-error").textContent = "";
}

// -------------------------
// Init
// -------------------------

document.addEventListener("DOMContentLoaded", () => {
  // Wire form
  const form = $("filters-form");
  form.addEventListener("submit", loadConversionsFromForm);

  $("reset-filters").addEventListener("click", () => {
    resetFilters();
    $("raw-json").textContent = "Awaiting data…";
  });

  // Set default campaign if provided globally
  if (DEFAULT_CAMPAIGN_ID) {
    $("campaign-id").value = DEFAULT_CAMPAIGN_ID;
  }

  // Initial loads
  resetFilters();
  loadNetworks();
});
