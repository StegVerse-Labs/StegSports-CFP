// js/index.js
// [CFP-BRACKET v2025-12-03-01]

// Registry of CFP games → event label + Partnerize campaign_id
// You can change these strings anytime without touching backend.
const CFP_GAMES = [
  {
    key: "rose-2025",
    bowl: "Rose Bowl Semifinal",
    date: "Jan 1, 2025 · Pasadena, CA",
    time: "5:00 PM ET",
    eventName: "Rose Bowl CFP Semifinal · Team 1 vs Team 4",
    campaignId: "CFP-ROSE-2025",
    groupSize: 4,
    maxRows: 2,
  },
  {
    key: "sugar-2025",
    bowl: "Sugar Bowl Semifinal",
    date: "Jan 1, 2025 · New Orleans, LA",
    time: "8:45 PM ET",
    eventName: "Sugar Bowl CFP Semifinal · Team 2 vs Team 3",
    campaignId: "CFP-SUGAR-2025",
    groupSize: 4,
    maxRows: 2,
  },
  {
    key: "title-2025",
    bowl: "CFP National Championship",
    date: "Jan 13, 2025 · Atlanta, GA",
    time: "7:30 PM ET",
    eventName: "College Football Playoff National Championship",
    campaignId: "CFP-TITLE-2025",
    groupSize: 4,
    maxRows: 2,
  },
];

// Render simple cards for each game
function renderGames() {
  const grid = document.getElementById("games-grid");
  if (!grid) return;
  grid.innerHTML = "";

  CFP_GAMES.forEach((g) => {
    const card = document.createElement("div");
    card.className = "game-card";

    const title = document.createElement("div");
    title.className = "game-title";
    title.textContent = g.bowl;
    card.appendChild(title);

    const meta = document.createElement("div");
    meta.className = "game-meta";
    meta.textContent = `${g.date} · ${g.time}`;
    card.appendChild(meta);

    const teams = document.createElement("div");
    teams.className = "teams";
    teams.innerHTML = `<span>${g.eventName}</span>`;
    card.appendChild(teams);

    const pills = document.createElement("div");
    const campaignPill = document.createElement("span");
    campaignPill.className = "pill campaign";
    campaignPill.textContent = `campaign_id: ${g.campaignId}`;
    pills.appendChild(campaignPill);
    card.appendChild(pills);

    const btnRow = document.createElement("div");
    btnRow.className = "btn-row";

    const ticketsBtn = document.createElement("button");
    ticketsBtn.className = "btn-primary";
    ticketsBtn.textContent = "Tickets";
    ticketsBtn.dataset.gameKey = g.key;
    ticketsBtn.addEventListener("click", () => {
      openTicketsForGame(g.key);
    });
    btnRow.appendChild(ticketsBtn);

    const copyBtn = document.createElement("button");
    copyBtn.className = "btn-ghost";
    copyBtn.textContent = "Copy event label";
    copyBtn.addEventListener("click", () => {
      navigator.clipboard
        .writeText(g.eventName)
        .catch(() => {});
    });
    btnRow.appendChild(copyBtn);

    card.appendChild(btnRow);

    grid.appendChild(card);
  });
}

// Build URL to tickets.html with query params
function openTicketsForGame(gameKey) {
  const game = CFP_GAMES.find((g) => g.key === gameKey);
  if (!game) return;

  const params = new URLSearchParams();
  params.set("event_name", game.eventName);
  params.set("campaign_id", game.campaignId);
  if (game.groupSize) params.set("group_size", String(game.groupSize));
  if (game.maxRows) params.set("max_rows", String(game.maxRows));

  // Navigate to tickets.html with these params; relative path is fine
  const target = `tickets.html?${params.toString()}`;
  window.location.href = target;
}

document.addEventListener("DOMContentLoaded", () => {
  renderGames();
});
