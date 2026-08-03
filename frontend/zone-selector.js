// frontend/zone-selector.js — Zone selector with geolocation auto-detect
const API_BASE = "http://localhost:8000";

async function loadZones() {
  const resp = await fetch(`${API_BASE}/api/zones`);
  return resp.json();
}

async function detectNearestZone() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) return reject(new Error("Geolocation not supported"));
    navigator.geolocation.getCurrentPosition(async (pos) => {
      const { latitude: lat, longitude: lon } = pos.coords;
      const resp = await fetch(`${API_BASE}/api/zones/nearest?lat=${lat}&lon=${lon}`);
      resolve(await resp.json());
    }, reject, { timeout: 8000 });
  });
}

async function renderZoneSelector(containerId, onSelect) {
  const container = document.getElementById(containerId);
  const zones = await loadZones();

  container.innerHTML = `
    <div class="zone-selector">
      <label for="zoneSelect">Select your delivery zone</label>
      <select id="zoneSelect">
        <option value="">— Choose a zone —</option>
        ${Object.entries(zones).map(([city, zoneList]) => `
          <optgroup label="${city}">
            ${zoneList.map(z => `<option value="${z.zoneId}" data-lat="${z.centerLat}" data-lon="${z.centerLon}">${z.displayName}</option>`).join("")}
          </optgroup>
        `).join("")}
      </select>
      <button id="detectBtn" type="button">📍 Use my current location</button>
      <p id="zoneHint" class="zone-hint"></p>
    </div>
  `;

  document.getElementById("detectBtn").addEventListener("click", async () => {
    const hint = document.getElementById("zoneHint");
    hint.textContent = "Detecting location…";
    try {
      const nearest = await detectNearestZone();
      const select = document.getElementById("zoneSelect");
      select.value = nearest.zoneId;
      hint.textContent = `✅ Auto-detected: ${nearest.displayName}`;
      onSelect?.(nearest);
    } catch {
      hint.textContent = "❌ Location access denied — please select manually.";
    }
  });

  document.getElementById("zoneSelect").addEventListener("change", (e) => {
    const opt = e.target.selectedOptions[0];
    if (opt?.value) {
      onSelect?.({
        zoneId: opt.value,
        displayName: opt.textContent,
        centerLat: parseFloat(opt.dataset.lat),
        centerLon: parseFloat(opt.dataset.lon),
      });
    }
  });
}