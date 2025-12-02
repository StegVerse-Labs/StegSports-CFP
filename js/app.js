// [SCFP-APP v1] CFP public pages for StegSports.
const StegCFP = (function () {
  const AB_STORAGE_KEY = "steg_cfp_ab_variant";

  function getABVariant() {
    try {
      const existing = window.localStorage.getItem(AB_STORAGE_KEY);
      if (existing === "A" || existing === "B") return existing;
      const assigned = Math.random() < 0.5 ? "A" : "B";
      window.localStorage.setItem(AB_STORAGE_KEY, assigned);
      return assigned;
    } catch (e) {
      // If localStorage blocked, random each time
      return Math.random() < 0.5 ? "A" : "B";
    }
  }

  async function loadJSON(path) {
    const resp = await fetch(path, { cache: "no-cache" });
    if (!resp.ok) {
      throw new Error(`Failed to load ${path}: ${resp.status}`);
    }
    return resp.json();
  }

  function setYear() {
    const els = document.querySelectorAll("#cfp-year");
    els.forEach(el => (el.textContent = new Date().getFullYear()));
  }

  function withABParams(url, partner, variant, teamId, gameId) {
    try {
      const u = new URL(url);
      u.searchParams.set("src", "stegcfp");
      u.searchParams.set("variant", variant);
      u.searchParams.set("partner", partner);
      if (teamId) u.searchParams.set("team", teamId);
      if (gameId) u.searchParams.set("game", gameId);
      return u.toString();
    } catch (e) {
      return url;
    }
  }

  // ---------- Helpers for data ----------

  function findTeam(teamsData, teamId) {
    return (teamsData.teams || []).find(t => t.id === teamId);
  }

  function findGame(team, gameId) {
    if (!team || !team.games) return null;
    return team.games.find(g => g.id === gameId);
  }

  // ---------- Overview page ----------

  async function initOverviewPage() {
    setYear();

    try {
      const [rankings, teams] = await Promise.all([
        loadJSON("data/rankings.json"),
        loadJSON("data/teams.json")
      ]);

      renderRankingsTable(rankings, teams);

      const meta = document.getElementById("cfp-last-updated");
      if (meta && rankings.last_updated) {
        const dt = new Date(rankings.last_updated);
        meta.textContent = `Updated ${dt.toLocaleString()}`;
      }
    } catch (err) {
      console.error(err);
      const table = document.getElementById("cfp-rankings-table");
      if (table && table.tBodies[0]) {
        table.tBodies[0].innerHTML =
          `<tr><td colspan="7">Unable to load rankings.</td></tr>`;
      }
    }
  }

  function renderRankingsTable(rankings, teamsData) {
    const tbody = document.querySelector("#cfp-rankings-table tbody");
    if (!tbody) return;

    const variant = getABVariant(); // "A" or "B"
    tbody.innerHTML = "";

    (rankings.top_12 || []).forEach(entry => {
      const tr = document.createElement("tr");

      const team = findTeam(teamsData, entry.team_id);
      const game = team ? findGame(team, entry.next_game_id) : null;

      // rank
      const tdRank = document.createElement("td");
      tdRank.textContent = entry.rank;
      tr.appendChild(tdRank);

      // team (link to team page)
      const tdTeam = document.createElement("td");
      const link = document.createElement("a");
      link.href = `team.html?team=${encodeURIComponent(entry.team_id)}`;
      link.textContent = entry.name;
      link.className = "cfp-team-name";
      tdTeam.appendChild(link);
      tr.appendChild(tdTeam);

      // record
      const tdRecord = document.createElement("td");
      tdRecord.textContent = entry.record || (team && team.record) || "";
      tr.appendChild(tdRecord);

      // conference
      const tdConf = document.createElement("td");
      tdConf.textContent = entry.conference || (team && team.conference) || "";
      tr.appendChild(tdConf);

      // seed
      const tdSeed = document.createElement("td");
      const chip = document.createElement("span");
      chip.className = "cfp-chip cfp-chip-primary";
      chip.textContent = `Seed ${entry.seed}`;
      tdSeed.appendChild(chip);
      tr.appendChild(tdSeed);

      // next game
      const tdNext = document.createElement("td");
      if (game) {
        tdNext.textContent = `${game.label} vs ${game.opponent}`;
      } else {
        tdNext.textContent = "TBD";
      }
      tr.appendChild(tdNext);

      // tickets (A/B between SeatGeek & StubHub)
      const tdTickets = document.createElement("td");
      const query =
        (game && game.seatgeek_query_override) ||
        (team && team.seatgeek_query) ||
        entry.name + " football";

      let primaryPartner, secondaryPartner;
      if (variant === "A") {
        primaryPartner = "seatgeek";
        secondaryPartner = "stubhub";
      } else {
        primaryPartner = "stubhub";
        secondaryPartner = "seatgeek";
      }

      // primary button
      const primaryBtn = document.createElement("a");
      primaryBtn.className = "cfp-btn";
      primaryBtn.target = "_blank";
      primaryBtn.rel = "noopener noreferrer";

      if (primaryPartner === "seatgeek") {
        primaryBtn.href = withABParams(
          StegSeatGeek.buildEventUrl(query),
          primaryPartner,
          variant,
          entry.team_id,
          game && game.id
        );
        primaryBtn.textContent = "SeatGeek";
      } else {
        primaryBtn.href = withABParams(
          StegStubHub.buildEventUrl(query),
          primaryPartner,
          variant,
          entry.team_id,
          game && game.id
        );
        primaryBtn.textContent = "StubHub";
      }

      tdTickets.appendChild(primaryBtn);

      // secondary link
      const secondaryLink = document.createElement("a");
      secondaryLink.className = "cfp-secondary-link";
      secondaryLink.style.marginLeft = "0.4rem";
      secondaryLink.style.fontSize = "0.75rem";
      secondaryLink.target = "_blank";
      secondaryLink.rel = "noopener noreferrer";

      if (secondaryPartner === "seatgeek") {
        secondaryLink.href = withABParams(
          StegSeatGeek.buildEventUrl(query),
          secondaryPartner,
          variant,
          entry.team_id,
          game && game.id
        );
        secondaryLink.textContent = "SeatGeek";
      } else {
        secondaryLink.href = withABParams(
          StegStubHub.buildEventUrl(query),
          secondaryPartner,
          variant,
          entry.team_id,
          game && game.id
        );
        secondaryLink.textContent = "StubHub";
      }

      tdTickets.appendChild(secondaryLink);

      tr.appendChild(tdTickets);
      tbody.appendChild(tr);
    });
  }

  // ---------- Team page ----------

  async function initTeamPage() {
    setYear();

    const params = new URLSearchParams(window.location.search);
    const teamId = params.get("team");

    if (!teamId) {
      document.body.innerHTML =
        "<p style='padding:1rem'>Missing team parameter.</p>";
      return;
    }

    try {
      const teamsData = await loadJSON("data/teams.json");
      const team = findTeam(teamsData, teamId.toUpperCase());

      if (!team) {
        document.body.innerHTML =
          "<p style='padding:1rem'>Team not found.</p>";
        return;
      }

      renderTeamHeader(team);
      renderTeamGames(team);
    } catch (err) {
      console.error(err);
      document.body.innerHTML =
        "<p style='padding:1rem'>Unable to load team data.</p>";
    }
  }

  function renderTeamHeader(team) {
    const titleEl = document.getElementById("team-page-title");
    const nameEl = document.getElementById("team-name");
    const metaEl = document.getElementById("team-meta");

    if (titleEl) titleEl.textContent = `${team.name} – StegSports CFP`;
    if (nameEl) nameEl.textContent = team.name;
    if (metaEl)
      metaEl.textContent = `${team.record} • ${team.conference}`;

    if (team.primary_color) {
      const hero = document.querySelector(".team-hero");
      if (hero) {
        hero.style.borderLeftColor = team.primary_color;
      }
    }
  }

  function renderTeamGames(team) {
    const tbody = document.querySelector("#team-games-table tbody");
    if (!tbody) return;

    const variant = getABVariant();
    tbody.innerHTML = "";

    (team.games || []).forEach(game => {
      const tr = document.createElement("tr");

      const tdDate = document.createElement("td");
      tdDate.textContent = game.date || "";
      tr.appendChild(tdDate);

      const tdOpp = document.createElement("td");
      tdOpp.textContent = game.opponent || "";
      tr.appendChild(tdOpp);

      const tdLoc = document.createElement("td");
      tdLoc.textContent = game.location || "";
      tr.appendChild(tdLoc);

      const tdImpact = document.createElement("td");
      tdImpact.textContent = game.importance || "";
      tr.appendChild(tdImpact);

      const tdTickets = document.createElement("td");
      const primaryPartner = variant === "A" ? "seatgeek" : "stubhub";
      const secondaryPartner = variant === "A" ? "stubhub" : "seatgeek";

      const query =
        game.seatgeek_query_override ||
        team.seatgeek_query ||
        `${team.name} vs ${game.opponent}`;

      // primary
      const primary = document.createElement("a");
      primary.className = "cfp-btn";
      primary.target = "_blank";
      primary.rel = "noopener noreferrer";

      if (primaryPartner === "seatgeek") {
        primary.href = withABParams(
          StegSeatGeek.buildEventUrl(query),
          primaryPartner,
          variant,
          team.id,
          game.id
        );
        primary.textContent = "SeatGeek";
      } else {
        primary.href = withABParams(
          StegStubHub.buildEventUrl(query),
          primaryPartner,
          variant,
          team.id,
          game.id
        );
        primary.textContent = "StubHub";
      }

      tdTickets.appendChild(primary);

      // secondary
      const secondary = document.createElement("a");
      secondary.className = "cfp-secondary-link";
      secondary.style.marginLeft = "0.4rem";
      secondary.style.fontSize = "0.75rem";
      secondary.target = "_blank";
      secondary.rel = "noopener noreferrer";

      if (secondaryPartner === "seatgeek") {
        secondary.href = withABParams(
          StegSeatGeek.buildEventUrl(query),
          secondaryPartner,
          variant,
          team.id,
          game.id
        );
        secondary.textContent = "SeatGeek";
      } else {
        secondary.href = withABParams(
          StegStubHub.buildEventUrl(query),
          secondaryPartner,
          variant,
          team.id,
          game.id
        );
        secondary.textContent = "StubHub";
      }

      tdTickets.appendChild(secondary);

      tr.appendChild(tdTickets);
      tbody.appendChild(tr);
    });

    if (!team.games || team.games.length === 0) {
      tbody.innerHTML =
        "<tr><td colspan='5'>No upcoming games listed.</td></tr>";
    }
  }

  return {
    initOverviewPage,
    initTeamPage,
    getABVariant
  };
})();
