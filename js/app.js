// js/app.js
// Shared helpers for CFP.StegSports.app

const API_BASE = "/api/tickets";

/**
 * Helper to call the ticket search endpoint.
 */
export async function searchTickets(params) {
  const url = new URL(`${API_BASE}/search`, window.location.origin);
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") {
      url.searchParams.set(k, String(v));
    }
  });

  const res = await fetch(url.toString(), {
    method: "GET",
    headers: { Accept: "application/json" },
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`API error ${res.status}: ${text || res.statusText}`);
  }

  return await res.json();
}

/**
 * Very simple experiment id – you can swap to cookies later.
 */
export function getExperimentId() {
  let existing = window.localStorage.getItem("cfp_experiment_id");
  if (!existing) {
    existing = crypto.randomUUID ? crypto.randomUUID() : String(Date.now());
    window.localStorage.setItem("cfp_experiment_id", existing);
  }
  return existing;
}
