// js/dashboard.js
// [CFP-DASHBOARD v2025-12-03-03]

const SCW_API_BASE =
  (typeof window !== "undefined" && window.CFP_API_BASE) ||
  "https://scw-api.onrender.com";

async function fetchJSON(path, params) {
  const url = new URL(SCW_API_BASE + path);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== "") {
        url.searchParams.set(k, String(v));
      }
    });
  }
  const res = await fetch(url.toString(), {
    headers: { Accept: "application/json" },
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HTTP ${res.status}: ${text}`);
  }
  return res.json();
}

// ---------------- Partnerize status ----------------

async function loadStatus() {
  const pill = document.getElementById("status-pill");
  const meta = document.getElementById("status-meta");
  const err = document.getElementById("status-error");

  pill.textContent = "Checking…";
  pill.classList.remove("ok", "bad");
  err.style.display = "none";
  err.textContent = "";

  try {
    const data = await fetchJSON("/v1/partnerize/status");

    const envOk = data.env_ok;
    const pingOk = data.network_ping_ok;

    if (envOk && pingOk) {
      pill.textContent = "Connected";
      pill.classList.add("ok");
    } else if (envOk && !pingOk) {
      pill.textContent = "Configured, ping failed";
      pill.classList.add("bad");
    } else {
      pill.textContent = "Not configured";
      pill.classList.add("bad");
    }

    meta.textContent = `Base URL: ${data.base_url} · Networks seen: ${
      data.network_count ?? "—"
    }`;

    if (data.error) {
      err.textContent = data.error;
      err.style.display = "block";
    }
  } catch (e) {
    pill.textContent = "Error";
    pill.classList.add("bad");
    meta.textContent = "";
    err.textContent = String(e);
    err.style.display = "block";
  }
}

// ---------------- Partnerize networks ----------------

async function loadNetworks() {
  const meta = document.getElementById("networks-meta");
  const table = document.getElementById("networks-table");
  const body = document.getElementById("networks-body");

  meta.textContent = "Loading…";
  table.style.display = "none";
  body.innerHTML = "";

  try {
    const data = await fetchJSON("/v1/partnerize/networks/summary");

    meta.textContent = `Networks: ${data.count ?? 0} (raw count: ${
      data.raw_count ?? "?"
    }) · execution time: ${data.execution_time ?? "n/a"}`;

    (data.items || []).forEach((n) => {
      const tr = document.createElement("tr");

      const tdId = document.createElement("td");
      tdId.textContent = n.id ?? "—";
      tr.appendChild(tdId);

      const tdName = document.createElement("td");
      tdName.textContent = n.name ?? "—";
      tr.appendChild(tdName);

      const tdLocale = document.createElement("td");
      tdLocale.textContent = n.locale ?? "—";
      tr.appendChild(tdLocale);

      const tdDesc = document.createElement("td");
      tdDesc.textContent = n.description ?? "";
      tr.appendChild(tdDesc);

      body.appendChild(tr);
    });

    table.style.display = "table";
  } catch (e) {
    meta.textContent = `Error loading networks: ${e}`;
    table.style.display = "none";
  }
}

// ---------------- Ticket click summary ----------------

function computeShare(count, total) {
  if (!total || total <= 0) return "0%";
  const pct = (count / total) * 100;
  return `${pct.toFixed(1)}%`;
}

async function loadClicks() {
  const meta = document.getElementById("clicks-meta");
  const tableProv = document.getElementById("clicks-table-provider");
  const bodyProv = document.getElementById("clicks-body-provider");
  const tableCamp = document.getElementById("clicks-table-campaign");
  const bodyCamp = document.getElementById("clicks-body-campaign");

  meta.textContent = "Loading…";
  tableProv.style.display = "none";
  bodyProv.innerHTML = "";
  tableCamp.style.display = "none";
  bodyCamp.innerHTML = "";

  try {
    const data = await fetchJSON("/v1/tickets/clicks/summary", { limit: 200 });

    const total = data.total_clicks || 0;
    const window = data.window || {};
    const byProvider = data.by_provider || {};
    const byCampaign = data.by_campaign || {};

    let windowText = "";
    if (window.start_ts && window.end_ts) {
      const start = new Date(window.start_ts * 1000);
      const end = new Date(window.end_ts * 1000);
      windowText = ` · window: ${start.toISOString()} → ${end.toISOString()}`;
    }

    meta.textContent = `Total logged clicks (last ${
      data.limit ?? 200
    }): ${total}${windowText}`;

    // Providers
    const providers = Object.keys(byProvider).sort();
    providers.forEach((name) => {
      const count = byProvider[name] || 0;
      const tr = document.createElement("tr");

      const tdProv = document.createElement("td");
      tdProv.textContent = name;
      tr.appendChild(tdProv);

      const tdCount = document.createElement("td");
      tdCount.textContent = String(count);
      tr.appendChild(tdCount);

      const tdShare = document.createElement("td");
      tdShare.textContent = computeShare(count, total);
      tr.appendChild(tdShare);

      bodyProv.appendChild(tr);
    });
    if (providers.length > 0) {
      tableProv.style.display = "table";
    }

    // Campaigns
    const campaigns = Object.keys(byCampaign).sort();
    campaigns.forEach((cid) => {
      const count = byCampaign[cid] || 0;
      const tr = document.createElement("tr");

      const label = cid === "none" ? "(none)" : cid;

      const tdCamp = document.createElement("td");
      tdCamp.textContent = label;
      tr.appendChild(tdCamp);

      const tdCount = document.createElement("td");
      tdCount.textContent = String(count);
      tr.appendChild(tdCount);

      const tdShare = document.createElement("td");
      tdShare.textContent = computeShare(count, total);
      tr.appendChild(tdShare);

      bodyCamp.appendChild(tr);
    });
    if (campaigns.length > 0) {
      tableCamp.style.display = "table";
    }
  } catch (e) {
    meta.textContent = `Error loading clicks: ${e}`;
    tableProv.style.display = "none";
    tableCamp.style.display = "none";
  }
}

// ---------------- Init ----------------

document.addEventListener("DOMContentLoaded", () => {
  loadStatus();
  loadNetworks();
  loadClicks();
});
