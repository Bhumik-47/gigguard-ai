// dashboard.js — Worker Dashboard controller
const API_BASE = "http://localhost:8000";

const THRESHOLDS = {
  temp:     { warn: 38, danger: 45 },
  aqi:      { warn: 150, danger: 300 },
  rainfall: { warn: 15, danger: 30 },
  wind:     { warn: 40, danger: 60 },
};

function getStatusClass(value, thresholds) {
  if (value >= thresholds.danger) return "status-danger";
  if (value >= thresholds.warn)   return "status-warn";
  return "status-ok";
}

function getStatusLabel(value, thresholds) {
  if (value >= thresholds.danger) return "🔴 Danger";
  if (value >= thresholds.warn)   return "🟡 Warning";
  return "🟢 Normal";
}

function renderPolicy(policy) {
  const badge = document.getElementById("policyBadge");
  badge.textContent = policy.status;
  badge.className = `badge ${policy.status.toLowerCase()}`;
  document.getElementById("policyZone").textContent    = policy.zone ?? "—";
  document.getElementById("policyCoverage").textContent = policy.coverage ?? "—";
  document.getElementById("policyPremium").textContent  = policy.premium ?? "—";
  document.getElementById("policyExpiry").textContent   = policy.validUntil ?? "—";
  document.getElementById("workerName").textContent     = policy.workerName ?? "Worker";
}

function renderEnvironment(env) {
  const metrics = [
    { key: "temp",     valId: "tempVal",  statusId: "tempStatus",  value: env.temperature_celsius, unit: "°C", thresholds: THRESHOLDS.temp },
    { key: "aqi",      valId: "aqiVal",   statusId: "aqiStatus",   value: env.aqi, unit: "", thresholds: THRESHOLDS.aqi },
    { key: "rainfall", valId: "rainVal",  statusId: "rainStatus",  value: env.rainfall_mm_per_hr, unit: "", thresholds: THRESHOLDS.rainfall },
    { key: "wind",     valId: "windVal",  statusId: "windStatus",  value: env.wind_speed_kmh, unit: "", thresholds: THRESHOLDS.wind },
  ];
  metrics.forEach(({ valId, statusId, value, unit, thresholds }) => {
    document.getElementById(valId).textContent = `${value}${unit}`;
    const el = document.getElementById(statusId);
    el.textContent  = getStatusLabel(value, thresholds);
    el.className    = `metric-status ${getStatusClass(value, thresholds)}`;
  });
  document.getElementById("lastUpdated").textContent =
    `Last updated: ${new Date(env.timestamp).toLocaleTimeString()}`;
}

function renderPayouts(records) {
  const tbody = document.getElementById("payoutTableBody");
  if (!records || records.length === 0) {
    tbody.innerHTML = `<tr><td colspan="4" class="empty">No payouts yet.</td></tr>`;
    return;
  }
  tbody.innerHTML = records.map(r => `
    <tr>
      <td>${r.date}</td>
      <td>${r.reason}</td>
      <td>${r.amount}</td>
      <td class="credited">${r.status}</td>
    </tr>
  `).join("");
}

async function loadDashboard() {
  try {
    // Fetch dashboard data from backend
    const dashResp = await fetch(`${API_BASE}/dashboard`);
    const dashData = await dashResp.json();
    renderPolicy({
      status: dashData.risk_level === "CRITICAL" ? "INACTIVE" : "ACTIVE",
      zone: dashData.location ?? "Mumbai",
      coverage: "₹500/shift",
      premium:  "₹12/shift",
      validUntil: new Date(Date.now() + 86400000).toLocaleString(),
      workerName: dashData.worker_name ?? "Worker",
    });
    renderPayouts(dashData.payout_history ?? []);

    // Fetch live environment (default to Mumbai coords)
    const lat = dashData.lat ?? 19.076;
    const lon = dashData.lon ?? 72.877;
    const envResp = await fetch(`${API_BASE}/api/environment?lat=${lat}&lon=${lon}`);
    const envData = await envResp.json();
    renderEnvironment(envData);
  } catch (err) {
    console.error("Dashboard load error:", err);
  }
}

// Load immediately, then refresh every 5 minutes
loadDashboard();
setInterval(loadDashboard, 5 * 60 * 1000);