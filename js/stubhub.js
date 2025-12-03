// js/stubhub.js
// StubHub-focused page.

import { searchTickets, getExperimentId } from "./app.js";

const form = document.querySelector("#cfp-form");
const btn = document.querySelector("#cfp-submit");
const resultsBox = document.querySelector("#results");

if (form && btn && resultsBox) {
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    resultsBox.innerHTML = "";
    btn.disabled = true;

    const data = new FormData(form);

    const params = {
      event_name: data.get("event_name") || "",
      location: data.get("location") || "",
      date: data.get("date") || "",
      group_size: Number(data.get("group_size") || "2"),
      max_rows: Number(data.get("max_rows") || "1"),
      provider: "stubHub", // override
      experiment_id: getExperimentId(),
    };

    try {
      const res = await searchTickets(params);
      renderResults(res);
    } catch (err) {
      console.error(err);
      resultsBox.innerHTML =
        '<div class="result-provider">Something went wrong loading tickets. Try again in a minute.</div>';
    } finally {
      btn.disabled = false;
    }
  });
}

function renderResults(res) {
  resultsBox.innerHTML = "";

  const heading = document.createElement("div");
  heading.className = "result-provider";
  heading.textContent = `StubHub page • Backend bucket: ${res.experiment_bucket}`;

  const group = document.createElement("div");
  group.className = "result-provider";
  group.textContent = `Group of ${res.group_size} ok on up to ${res.max_rows} row(s).`;

  const list = document.createElement("div");
  list.className = "link-list";

  res.links.forEach((link) => {
    const a = document.createElement("a");
    a.href = link.url;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    a.className = "cta" + (link.provider === "stubHub" ? " primary" : "");
    a.innerHTML = `
      <span class="label">${link.label}</span>
      <span class="meta">${
        link.provider === "stubHub" ? "StubHub preferred" : "Compare on SeatGeek"
      }</span>
    `;
    list.appendChild(a);
  });

  resultsBox.appendChild(heading);
  resultsBox.appendChild(group);
  resultsBox.appendChild(list);
}
