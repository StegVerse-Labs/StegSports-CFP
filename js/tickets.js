// js/tickets.js
// [CFP-TICKETS-UI v2025-12-03-02]

const API_BASE =
  (typeof window !== "undefined" && window.CFP_API_BASE) ||
  "https://scw-api.onrender.com";

function $(id) {
  return document.getElementById(id);
}

async function fetchJSON(path, params) {
  const url = new URL(API_BASE + path);

  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") {
        url.searchParams.set(key, String(value));
      }
    });
  }

  const res = await fetch(url.toString(), {
    method: "GET",
    headers: { Accept: "application/json" },
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HTTP ${res.status}: ${text}`);
  }

  return res.json();
}

function resetForm() {
  $("event-name").value = "";
  $("group-size").value = "";
  $("max-rows").value = "";
  $("campaign-id").value = "";
  $("form-error").style.display = "none";
  $("form-error").textContent = "";
  $("results-card").style.display = "none";
  $("raw-json").textContent = "Awaiting search…";
}

function buildProviderCard(link) {
  const card = document.createElement("div");
  card.className = "provider-card";

  const name = document.createElement("div");
  name.className = "provider-name";
  name.textContent =
    link.provider === "seatGeek" ? "SeatGeek" : "StubHub";
  card.appendChild(name);

  const meta = document.createElement("div");
  meta.className = "provider-meta";
  const isPrimary = link.role === "primary";
  meta.textContent = isPrimary
    ? "Primary for this request"
    : "Secondary (still available)";
  card.appendChild(meta);

  const actions = document.createElement("div");
  actions.className = "provider-actions";

  const mainBtn = document.createElement("a");
  mainBtn.href = API_BASE + link.click_url;
  mainBtn.target = "_blank";
  mainBtn.rel = "noopener noreferrer";
  mainBtn.textContent = "Open via StegSports";
  actions.appendChild(mainBtn);

  const rawBtn = document.createElement("a");
  rawBtn.href = link.direct_url;
  rawBtn.target = "_blank";
  rawBtn.rel = "noopener noreferrer";
  rawBtn.textContent = "Open provider direct";
  rawBtn.className = "secondary-btn";
  actions.appendChild(rawBtn);

  card.appendChild(actions);

  return card;
}

async function handleSubmit(evt) {
  evt.preventDefault();

  const eventName = $("event-name").value.trim();
  const groupSize = $("group-size").value.trim();
  const maxRows = $("max-rows").value;
  const campaignId = $("campaign-id").value.trim();

  const errorBox = $("form-error");
  const submitBtn = $("submit-btn");

  errorBox.style.display = "none";
  errorBox.textContent = "";

  if (!eventName) {
    errorBox.style.display = "block";
    errorBox.textContent = "Please enter an event name.";
    return;
  }

  submitBtn.disabled = true;
  submitBtn.textContent = "Searching…";

  try {
    const params = {
      event_name: eventName,
    };
    if (groupSize) params.group_size = Number(groupSize);
    if (maxRows) params.max_rows = Number(maxRows);
    if (campaignId) params.campaign_id = campaignId;

    const data = await fetchJSON("/v1/tickets/search", params);

    $("raw-json").textContent = JSON.stringify(data, null, 2);

    const primaryProvider = data.primary_provider || "seatGeek";

    const pill = $("primary-pill");
    pill.textContent = `Primary: ${
      primaryProvider === "seatGeek" ? "SeatGeek" : "StubHub"
    }`;
    pill.className = "pill primary";

    const campaignText = data.campaign_id
      ? ` · campaign: ${data.campaign_id}`
      : "";

    $("results-meta").textContent = `Mode: ${
      data.split?.mode || "auto"
    } · SeatGeek primary share: ${
      data.split?.seatGeek_percent ?? "?"
    }%${campaignText}`;

    const grid = $("provider-grid");
    grid.innerHTML = "";
    (data.links || []).forEach((link) => {
      const card = buildProviderCard(link);
      grid.appendChild(card);
    });

    $("results-card").style.display = "block";
  } catch (err) {
    errorBox.style.display = "block";
    errorBox.textContent = err.message || String(err);
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Search tickets";
  }
}

document.addEventListener("DOMContentLoaded", () => {
  $("tickets-form").addEventListener("submit", handleSubmit);
  $("reset-btn").addEventListener("click", resetForm);
});
