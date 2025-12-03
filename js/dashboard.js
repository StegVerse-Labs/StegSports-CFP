// js/dashboard.js
// [CFP-DASHBOARD v2025-12-03-01]

const SCW_API_BASE = "https://scw-api.onrender.com"; // change here if needed

async function fetchJSON(path) {
  const url = `${SCW_API_BASE}${path}`;
  const res = await fetch(url, { headers: { Accept: "application/json" } });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HTTP ${res.status}: ${text}`);
  }
  return res.json();
}

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

document.addEventListener("DOMContentLoaded", () => {
  loadStatus();
  loadNetworks();
});
