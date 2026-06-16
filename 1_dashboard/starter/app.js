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
      <td>${v.last_service_date}</td>
      <td>${v.assigned_driver ?? "—"}</td>
    `;
    tbody.appendChild(tr);
  }
}

loadVehicles()
  .then((vehicles) => {
    renderSummary(vehicles);
    renderTable(vehicles);
  })
  .catch((err) => {
    console.error(err);
    document.getElementById("vehicle-tbody").innerHTML =
      `<tr><td colspan="8">Failed to load vehicle data.</td></tr>`;
  });
