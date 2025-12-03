// js/dashboard.js
// [CFP-DASHBOARD v2025-12-03-14]

const SCW_API_BASE =
  (typeof window !== "undefined" && window.CFP_API_BASE) ||
  "https://scw-api.onrender.com";

// Mapping Partnerize campaign_id → CFP game metadata
// Keep this in sync with js/index.js CFP_GAMES.
const CAMPAIGN_META = {
  "CFP-ROSE-2025": {
    gameLabel: "Rose Bowl Semifinal",
    eventName: "Rose Bowl CFP Semifinal · Team 1 vs Team 4",
    groupSize: 4,
    maxRows: 2,
  },
  "CFP-SUGAR-2025": {
    gameLabel: "Sugar Bowl Semifinal",
    eventName: "Sugar Bowl CFP Semifinal · Team 2 vs Team 3",
    groupSize: 4,
    maxRows: 2,
  },
  "CFP-TITLE-2025": {
    gameLabel: "CFP National Championship",
    eventName: "College Football Playoff National Championship",
    groupSize: 4,
    maxRows: 2,
  },
};

// In-memory snapshot of merged affiliate data for export
let AFFILIATE_EXPORT = {
  byCampaign: [],
  meta: {},
};

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

function getSelectedDays() {
  const sel = document.getElementById("window-select");
  if (!sel) return 30;
  const v = Number(sel.value || 30);
  if (!Number.isFinite(v) || v <= 0) return 30;
  return v;
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

// ---------------- Ticket click summary + conversions ----------------

function computeShare(count, total) {
  if (!total || total <= 0) return "0%";
  const pct = (count / total) * 100;
  return `${pct.toFixed(1)}%`;
}

function formatCurrency(amount, currency) {
  if (amount == null) return "—";
  const num = Number(amount);
  if (!isFinite(num)) return "—";
  const code = currency || "USD";
  try {
    return new Intl.NumberFormat(undefined, {
      style: "currency",
      currency: code,
      maximumFractionDigits: 2,
    }).format(num);
  } catch {
    return `${num.toFixed(2)} ${code}`;
  }
}

function computeRpc(revenue, clicks) {
  if (!clicks || clicks <= 0 || revenue == null) return "—";
  const val = Number(revenue) / clicks;
  if (!isFinite(val)) return "—";
  return val.toFixed(2);
}

async function loadClicks() {
  const meta = document.getElementById("clicks-meta");
  const tableProv = document.getElementById("clicks-table-provider");
  const bodyProv = document.getElementById("clicks-body-provider");
  const tableCamp = document.getElementById("clicks-table-campaign");
  const bodyCamp = document.getElementById("clicks-body-campaign");
  const exportMeta = document.getElementById("export-meta");

  const days = getSelectedDays();

  meta.textContent = `Loading… (conversions: last ${days} days)`;
  tableProv.style.display = "none";
  tableCamp.style.display = "none";
  bodyProv.innerHTML = "";
  bodyCamp.innerHTML = "";

  AFFILIATE_EXPORT = { byCampaign: [], meta: {} };
  exportMeta.textContent =
    "CSV uses current click + conversion data in tables below.";

  try {
    // 1) Click summary from SCW
    const clickData = await fetchJSON("/v1/tickets/clicks/summary", {
      limit: 200,
    });

    const total = clickData.total_clicks || 0;
    const window = clickData.window || {};
    const byProvider = clickData.by_provider || {};
    const byCampaign = clickData.by_campaign || {};

    let windowText = "";
    if (window.start_ts && window.end_ts) {
      const start = new Date(window.start_ts * 1000);
      const end = new Date(window.end_ts * 1000);
      windowText = ` · click window: ${start.toISOString()} → ${end.toISOString()}`;
    }

    meta.textContent = `Total logged clicks (last ${
      clickData.limit ?? 200
    }): ${total}${windowText} · conversions window: last ${days} days`;

    // Providers table
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

    // 2) Determine campaign IDs that actually have clicks
    const campaignIds = Object.keys(byCampaign).filter((cid) => cid !== "none");
    if (campaignIds.length === 0) {
      tableCamp.style.display = "none";
      exportMeta.textContent =
        "No campaign clicks yet — CSV export will be empty.";
      return;
    }

    // 3) Fetch Partnerize conversions for those campaigns with the selected window
    let convData;
    try {
      convData = await fetchJSON("/v1/partnerize/conversions/summary", {
        campaign_ids: campaignIds.join(","),
        days,
      });
    } catch (e) {
      // If conversions call fails, at least show click counts
      meta.textContent += ` · conversions error: ${e}`;
      tableCamp.style.display = "none";
      exportMeta.textContent =
        "Conversions API error — CSV will include clicks only.";
      return;
    }

    const convMap = {};
    (convData.campaigns || []).forEach((c) => {
      convMap[String(c.campaign_id)] = c;
    });

    const convWindow = convData.window || {};
    if (convWindow.start_date && convWindow.end_date) {
      meta.textContent += ` · conv window: ${convWindow.start_date} → ${convWindow.end_date}`;
    }

    // 4) Build by-campaign table (clicks + conversions + revenue)
    const campaignsSorted = Object.keys(byCampaign).sort();
    const exportRows = [];

    campaignsSorted.forEach((cid) => {
      const clicks = byCampaign[cid] || 0;
      const label = cid === "none" ? "(none)" : cid;

      const stats = convMap[cid] || {};
      const conv = stats.conversions ?? 0;
      const rev = stats.revenue ?? null;
      const currency = stats.currency || "USD";
      const rpc = computeRpc(rev, clicks);

      const metaInfo = CAMPAIGN_META[cid] || {};
      const gameLabel = metaInfo.gameLabel || "";

      const tr = document.createElement("tr");

      const tdGame = document.createElement("td");
      tdGame.textContent = gameLabel || "—";
      tr.appendChild(tdGame);

      const tdCamp = document.createElement("td");
      tdCamp.textContent = label;
      tr.appendChild(tdCamp);

      const tdClicks = document.createElement("td");
      tdClicks.textContent = String(clicks);
      tr.appendChild(tdClicks);

      const tdConv = document.createElement("td");
      tdConv.textContent = conv == null ? "—" : String(conv);
      tr.appendChild(tdConv);

      const tdRev = document.createElement("td");
      tdRev.textContent =
        rev == null ? "—" : formatCurrency(rev, currency);
      tr.appendChild(tdRev);

      const tdRpc = document.createElement("td");
      tdRpc.textContent = rpc === "—" ? "—" : `${rpc} / click`;
      tr.appendChild(tdRpc);

      const tdActions = document.createElement("td");
      if (label !== "(none)") {
        const a = document.createElement("a");
        a.className = "link-btn";
        a.textContent = "Tickets";
        const params = new URLSearchParams();
        if (metaInfo.eventName) {
          params.set("event_name", metaInfo.eventName);
        }
        params.set("campaign_id", cid);
        if (metaInfo.groupSize) {
          params.set("group_size", String(metaInfo.groupSize));
        }
        if (metaInfo.maxRows) {
          params.set("max_rows", String(metaInfo.maxRows));
        }
        a.href = `tickets.html?${params.toString()}`;
        tdActions.appendChild(a);
      } else {
        tdActions.textContent = "—";
      }
      tr.appendChild(tdActions);

      bodyCamp.appendChild(tr);

      // collect for CSV
      exportRows.push({
        campaign_id: cid,
        game_label: gameLabel || null,
        clicks,
        conversions: conv,
        revenue: rev,
        currency,
        revenue_per_click: rpc === "—" ? null : Number(rpc),
      });
    });

    tableCamp.style.display = "table";

    AFFILIATE_EXPORT = {
      byCampaign: exportRows,
      meta: {
        total_clicks: total,
        click_window: window,
        conv_window: convWindow,
        conv_window_days: days,
        generated_at: new Date().toISOString(),
      },
    };
    exportMeta.textContent =
      "CSV is ready — includes one row per campaign with game, clicks, conversions, and revenue for the selected window.";
  } catch (e) {
    meta.textContent = `Error loading clicks: ${e}`;
    tableProv.style.display = "none";
    tableCamp.style.display = "none";
    AFFILIATE_EXPORT = { byCampaign: [], meta: {} };
    exportMeta.textContent =
      "Error loading data — CSV export is not available.";
  }
}

// ---------------- CSV export ----------------

function escapeCsvField(val) {
  if (val === null || val === undefined) return "";
  const s = String(val);
  if (/[",\n]/.test(s)) {
    // escape inner quotes
    return `"${s.replace(/"/g, '""')}"`;
  }
  return s;
}

function buildCsvFromExport() {
  const rows = AFFILIATE_EXPORT.byCampaign || [];
  if (!rows.length) {
    return null;
  }

  const header = [
    "campaign_id",
    "game_label",
    "clicks",
    "conversions",
    "revenue",
    "currency",
    "revenue_per_click",
    "generated_at",
    "click_window_start_ts",
    "click_window_end_ts",
    "conv_window_days",
    "conv_window_start_date",
    "conv_window_end_date",
  ];

  const meta = AFFILIATE_EXPORT.meta || {};
  const clickWindow = meta.click_window || {};
  const convWindow = meta.conv_window || {};

  const csvLines = [header.join(",")];

  rows.forEach((r) => {
    const line = [
      escapeCsvField(r.campaign_id),
      escapeCsvField(r.game_label),
      escapeCsvField(r.clicks),
      escapeCsvField(r.conversions),
      escapeCsvField(r.revenue),
      escapeCsvField(r.currency),
      escapeCsvField(r.revenue_per_click),
      escapeCsvField(meta.generated_at || ""),
      escapeCsvField(clickWindow.start_ts || ""),
      escapeCsvField(clickWindow.end_ts || ""),
      escapeCsvField(meta.conv_window_days || ""),
      escapeCsvField(convWindow.start_date || ""),
      escapeCsvField(convWindow.end_date || ""),
    ].join(",");
    csvLines.push(line);
  });

  return csvLines.join("\n");
}

function downloadCsv() {
  const btn = document.getElementById("export-btn");
  const exportMeta = document.getElementById("export-meta");

  const csv = buildCsvFromExport();
  if (!csv) {
    exportMeta.textContent =
      "No exportable data yet — make sure clicks and conversions are loaded.";
    return;
  }

  try {
    btn.disabled = true;
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);

    const a = document.createElement("a");
    const ts = new Date().toISOString().replace(/[:.]/g, "-");
    a.href = url;
    a.download = `cfp-affiliate-report-${ts}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    exportMeta.textContent =
      "CSV downloaded — includes game names and the selected conversions window.";
  } finally {
    btn.disabled = false;
  }
}

// ---------------- Init ----------------

document.addEventListener("DOMContentLoaded", () => {
  const exportBtn = document.getElementById("export-btn");
  const windowSelect = document.getElementById("window-select");
  const refreshBtn = document.getElementById("refresh-btn");

  if (exportBtn) {
    exportBtn.addEventListener("click", downloadCsv);
  }
  if (windowSelect) {
    windowSelect.addEventListener("change", () => {
      loadClicks();
    });
  }
  if (refreshBtn) {
    refreshBtn.addEventListener("click", () => {
      loadClicks();
    });
  }

  loadStatus();
  loadNetworks();
  loadClicks();
});
