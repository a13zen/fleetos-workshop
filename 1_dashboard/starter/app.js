async function loadVehicles() {
  const res = await fetch("data/vehicles.json");
  if (!res.ok) {
    throw new Error(`Failed to load vehicle data: ${res.status}`);
  }
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

function renderMaintenanceWidget(vehicles) {
  const now = Date.now();
  const thirtyDaysMs = 30 * 24 * 60 * 60 * 1000;

  const dueSoon = vehicles
    .filter((v) => {
      const serviceTime = new Date(v.next_service_date).getTime();
      const daysUntil = (serviceTime - now) / (24 * 60 * 60 * 1000);
      return daysUntil <= 30;
    })
    .map((v) => {
      const serviceTime = new Date(v.next_service_date).getTime();
      const daysUntil = Math.ceil((serviceTime - now) / (24 * 60 * 60 * 1000));
      return { ...v, daysUntil };
    })
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
      const isOverdue = v.daysUntil < 0;
      const daysLabel = isOverdue
        ? `${Math.abs(v.daysUntil)} day${Math.abs(v.daysUntil) !== 1 ? "s" : ""} overdue`
        : v.daysUntil === 0
        ? "due today"
        : `${v.daysUntil} day${v.daysUntil !== 1 ? "s" : ""} remaining`;

      item.innerHTML = `
        <span class="maint-id">${v.id}</span>
        <span class="maint-vehicle">${v.make} ${v.model} (${v.year})</span>
        <span class="maint-date">${v.next_service_date}</span>
        <span class="maint-days ${isOverdue ? "maint-overdue" : "maint-soon"}">${daysLabel}</span>
      `;
      list.appendChild(item);
    }

    section.appendChild(list);
  }

  // Insert between summary stats and vehicle table panel
  const tablePanelSection = document.querySelector(".panel");
  tablePanelSection.parentNode.insertBefore(section, tablePanelSection);
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
      <td>${v.last_service_date}</td>
      <td>${v.next_service_date}</td>
      <td>${v.assigned_driver ?? "—"}</td>
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
