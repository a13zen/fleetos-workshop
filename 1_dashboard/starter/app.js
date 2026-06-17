const esc = (s) => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

async function loadVehicles() {
  const res = await fetch("data/vehicles.json");
  if (!res.ok) {
    throw new Error(`Failed to load vehicle data: ${res.status}`);
  }
  return res.json();
}

function formatKm(km) {
  if (typeof km !== 'number') return '—';
  return km.toLocaleString("de-DE") + " km";
}

function renderSummary(vehicles) {
  const count = (status) => vehicles.filter((v) => v.status === status).length;
  document.getElementById("stat-total").textContent = vehicles.length;
  document.getElementById("stat-active").textContent = count("active");
  document.getElementById("stat-maintenance").textContent = count("maintenance");
  document.getElementById("stat-overdue").textContent = count("overdue");
}

function renderMaintenanceWidget(vehicles) {
  const now = Date.now();

  const dueSoon = vehicles
    .filter((v) => v.status !== 'retired')
    .map((v) => {
      const serviceTime = new Date(v.next_service_date).getTime();
      const daysUntilRaw = (serviceTime - now) / (24 * 60 * 60 * 1000);
      const daysUntil = Math.ceil(daysUntilRaw);
      return { ...v, daysUntilRaw, daysUntil };
    })
    .filter((v) => v.daysUntilRaw <= 30)
    .sort((a, b) => a.daysUntil - b.daysUntil);

  const section = document.createElement("section");
  section.className = "panel maintenance-widget";
  section.setAttribute("aria-label", "Maintenance due soon");

  const heading = document.createElement("h2");
  heading.textContent = "Maintenance Due Soon";
  section.appendChild(heading);

  if (dueSoon.length === 0) {
    const msg = document.createElement("p");
    msg.className = "no-maintenance";
    msg.textContent = "No upcoming maintenance in the next 30 days.";
    section.appendChild(msg);
  } else {
    const list = document.createElement("div");
    list.className = "maintenance-list";

    for (const v of dueSoon) {
      const item = document.createElement("div");
      item.className = "maintenance-item";
      const isOverdue = v.daysUntilRaw < 0;
      const daysLabel = isOverdue
        ? `${Math.abs(v.daysUntil)} day${Math.abs(v.daysUntil) !== 1 ? "s" : ""} overdue`
        : v.daysUntil === 0
        ? "due today"
        : `${v.daysUntil} day${v.daysUntil !== 1 ? "s" : ""} remaining`;

      item.innerHTML = `
        <span class="maint-id">${esc(v.id)}</span>
        <span class="maint-vehicle">${esc(v.make)} ${esc(v.model)} (${esc(v.year)})</span>
        <span class="maint-date">${esc(v.next_service_date)}</span>
        <span class="maint-days ${isOverdue ? "maint-overdue" : "maint-soon"}">${daysLabel}</span>
      `;
      list.appendChild(item);
    }

    section.appendChild(list);
  }

  // Insert between summary stats and vehicle table panel
  const tablePanelSection = document.getElementById('fleet-panel');
  if (tablePanelSection) {
    tablePanelSection.parentNode.insertBefore(section, tablePanelSection);
  }
}

function renderTable(vehicles) {
  const tbody = document.getElementById("vehicle-tbody");
  tbody.innerHTML = "";

  for (const v of vehicles) {
    const tr = document.createElement("tr");
    const safeStatus = ['active','maintenance','overdue','retired'].includes(v.status) ? v.status : 'unknown';
    tr.innerHTML = `
      <td>${esc(v.id)}</td>
      <td>${esc(v.make)} ${esc(v.model)} (${esc(v.year)})</td>
      <td><span class="status-pill status-${safeStatus}">${esc(v.status)}</span></td>
      <td class="col-location">${esc(v.location)}</td>
      <td class="num">${formatKm(v.mileage_km)}</td>
      <td>${esc(v.last_service_date)}</td>
      <td>${esc(v.next_service_date)}</td>
      <td>${esc(v.assigned_driver ?? "—")}</td>
    `;
    tbody.appendChild(tr);
  }
}

loadVehicles()
  .then((vehicles) => {
    renderSummary(vehicles);
    renderMaintenanceWidget(vehicles);
    renderTable(vehicles);
  })
  .catch((err) => {
    console.error(err);
    document.getElementById("vehicle-tbody").innerHTML =
      `<tr><td colspan="8">Failed to load vehicle data.</td></tr>`;
  });
