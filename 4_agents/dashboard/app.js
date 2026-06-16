const API_BASE = "http://localhost:8001";

function setDataSourceBadge(source) {
  const badge = document.getElementById("data-source-badge");
  if (!badge) return;
  if (source === "live") {
    badge.textContent = "Live API";
    badge.classList.remove("static");
    badge.classList.add("live");
  } else {
    badge.textContent = "Static data";
    badge.classList.remove("live");
    badge.classList.add("static");
  }
}

async function loadVehicles() {
  try {
    const res = await fetch(`${API_BASE}/vehicles`);
    if (res.ok) {
      setDataSourceBadge("live");
      return res.json();
    }
  } catch (_) {
    // API not running, fall through to static data
  }
  const res = await fetch("data/vehicles.json");
  if (!res.ok) {
    throw new Error(`Failed to load vehicle data: ${res.status}`);
  }
  setDataSourceBadge("static");
  return res.json();
}

function formatKm(km) {
  return km.toLocaleString("de-DE") + " km";
}

function renderSummary(vehicles) {
  const count = (status) => vehicles.filter((v) => v.status === status).length;
  document.getElementById("stat-total").textContent = vehicles.length;
  document.getElementById("stat-active").textContent = count("active");
  document.getElementById("stat-maintenance").textContent = count("maintenance");
  document.getElementById("stat-overdue").textContent = count("overdue");
}

function renderTable(vehicles) {
  const tbody = document.getElementById("vehicle-tbody");
  tbody.innerHTML = "";

  for (const v of vehicles) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${v.id}</td>
      <td>${v.make} ${v.model} (${v.year})</td>
      <td><span class="status-pill status-${v.status}">${v.status}</span></td>
      <td class="col-location">${v.location}</td>
      <td class="num">${formatKm(v.mileage_km)}</td>
      <td>${v.last_service_date ?? "—"}</td>
      <td>${v.next_service_date ?? "—"}</td>
      <td>${v.assigned_driver ?? "—"}</td>
    `;
    tbody.appendChild(tr);
  }
}

function renderMaintenanceSoon(vehicles) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const cutoff = new Date(today);
  cutoff.setDate(cutoff.getDate() + 30);

  const due = vehicles
    .filter((v) => {
      const d = new Date(v.next_service_date);
      return d >= today && d <= cutoff;
    })
    .map((v) => ({
      ...v,
      daysUntil: Math.round((new Date(v.next_service_date) - today) / 86400000),
    }))
    .sort((a, b) => a.daysUntil - b.daysUntil);

  const container = document.getElementById("maintenance-list");
  if (due.length === 0) {
    container.innerHTML = `<p class="no-maintenance">No upcoming maintenance</p>`;
    return;
  }
  container.innerHTML = due
    .map(
      (v) => `
      <div class="maintenance-item">
        <span class="maintenance-id">${v.id}</span>
        <span class="maintenance-vehicle">${v.make} ${v.model}</span>
        <span class="maintenance-days">${v.daysUntil === 0 ? "Today" : `${v.daysUntil}d`}</span>
      </div>`
    )
    .join("");
}

async function loadAgentBriefing() {
  const container = document.getElementById("briefing-list");
  let rows;
  try {
    const res = await fetch("./briefing.json", { cache: "no-store" });
    if (!res.ok) return;
    rows = await res.json();
  } catch (_) {
    return;
  }
  if (!Array.isArray(rows) || rows.length === 0) return;

  const el = (tag, cls, text) => {
    const n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  };
  const riskClass = (r) =>
    ["low", "medium", "high"].includes(String(r).toLowerCase())
      ? `risk-${String(r).toLowerCase()}`
      : "risk-unknown";

  container.replaceChildren(
    ...rows.map((r) => {
      const item = el("div", "briefing-item");
      item.append(
        el("span", "briefing-id", r.vehicle_id),
        el("span", `status-pill ${riskClass(r.risk)}`, r.risk),
        el("span", "briefing-action", r.action),
        el("span", "briefing-why", r.why)
      );
      return item;
    })
  );
}

function applyFilters(vehicles) {
  const status = document.getElementById("filter-status").value;
  const location = document.getElementById("filter-location").value.toLowerCase().trim();
  return vehicles.filter((v) => {
    if (status && v.status !== status) return false;
    if (location && !v.location.toLowerCase().includes(location)) return false;
    return true;
  });
}

loadAgentBriefing();

loadVehicles()
  .then((vehicles) => {
    renderSummary(vehicles);
    renderMaintenanceSoon(vehicles);
    renderTable(vehicles);

    const statusEl = document.getElementById("filter-status");
    const locationEl = document.getElementById("filter-location");
    const clearEl = document.getElementById("filter-clear");

    function onFilter() {
      renderTable(applyFilters(vehicles));
    }

    statusEl.addEventListener("change", onFilter);
    locationEl.addEventListener("input", onFilter);
    clearEl.addEventListener("click", () => {
      statusEl.value = "";
      locationEl.value = "";
      renderTable(vehicles);
    });
  })
  .catch((err) => {
    console.error(err);
    document.getElementById("vehicle-tbody").innerHTML =
      `<tr><td colspan="8">Failed to load vehicle data.</td></tr>`;
  });
