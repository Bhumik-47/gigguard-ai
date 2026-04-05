/**
 * GigGuard AI — Consolidated Script v4.0
 * Reusable across: dashboard.html, risk-monitor.html, payout.html
 */

document.addEventListener("DOMContentLoaded", () => {
    // 1. --- AUTHENTICATION GATEKEEPER ---
    // This logic ensures only logged-in users can see the dashboard.
    const auth = sessionStorage.getItem('gigguard_auth');
    const path = window.location.pathname;

    // If we are NOT on the login page (index.html) and not authenticated, kick back to login
    if (!path.endsWith('index.html') && path !== '/' && path !== '') {
        if (auth !== 'true') {
            console.warn("Unauthorized access. Redirecting to login...");
            window.location.replace('index.html');
            return; // Stop script execution
        }
    }

    // 2. --- DASHBOARD DATA INITIALIZATION ---
    // Only runs if the specific UI elements exist on the current page.
    if (document.getElementById('apiStatusText')) {
        fetchAPI('/dashboard', (data) => {
            console.log("Live API Data Loaded:", data);
            
            // Update UI with real-time data
            if (data.current_risk) {
                renderAICard(data.current_risk);
                renderFraudCard(data.current_risk);
            }
        }, () => {
            console.log("Backend not detected. Running in Demo/Fallback mode.");
        });
    }

    // 3. --- START GLOBAL UI EFFECTS ---
    animateScoreBars();
    initTooltips();
});

/* =====================================================================
   CORE ENGINE: API FETCH & STATUS
   ===================================================================== */

async function fetchAPI(endpoint, onSuccess, onFallback) {
    setApiStatus('loading');
    try {
        // NOTE: Replace 127.0.0.1 with your production backend URL once deployed
        const res = await fetch(`http://127.0.0.1:8000${endpoint}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        setApiStatus('live');
        onSuccess(data);
    } catch (err) {
        console.warn(`[GigGuard] API unavailable (${endpoint}):`, err.message);
        setApiStatus('demo');
        if (onFallback) onFallback();
    }
}

function setApiStatus(state) {
    const text = document.getElementById('apiStatusText');
    const dot = document.getElementById('apiStatusDot');
    if (!text) return;

    const map = { 
        loading: 'Connecting...', 
        live: 'Live Data ✅', 
        demo: 'Demo Mode ⚠️' 
    };
    text.textContent = map[state] || state;
    if (dot) dot.className = `api-dot ${state}`;
}

/* =====================================================================
   CORE ENGINE: AI RISK & FRAUD LOGIC
   ===================================================================== */

function renderExplanation(data) {
    const { rainfall = 0, aqi = 0, wind_speed = 0, payout = 0, payout_triggered = false } = data;
    const raw = typeof data.risk_score === 'number' ? data.risk_score : 0;
    const score = raw <= 1 ? Math.round(raw * 100) : Math.round(raw);

    const factors = [];
    const reasons = [];

    if (rainfall >= 50) {
        const contrib = Math.min(42, Math.round((rainfall - 50) / 80 * 35 + 12));
        factors.push({ label: '🌧 Rainfall', value: `${rainfall} mm/hr`, severity: rainfall >= 80 ? 'critical' : 'high', contribution: contrib });
        reasons.push(`Rainfall ${rainfall}mm/hr exceeds safe threshold — +${contrib}% risk`);
    }
    if (aqi >= 250) {
        const contrib = Math.min(28, Math.round((aqi - 250) / 200 * 20 + 8));
        factors.push({ label: '💨 Air Quality', value: `AQI ${aqi}`, severity: aqi >= 300 ? 'critical' : 'high', contribution: contrib });
        reasons.push(`AQI ${aqi} classified Hazardous — +${contrib}% disruption index`);
    }
    if (wind_speed >= 45) {
        const contrib = Math.min(18, Math.round((wind_speed - 45) / 45 * 12 + 5));
        factors.push({ label: '🌬 Wind Speed', value: `${wind_speed} km/h`, severity: wind_speed >= 65 ? 'critical' : 'elevated', contribution: contrib });
        reasons.push(`Wind ${wind_speed}km/h exceeds operational limit — visibility risk`);
    }

    let tier = 'Below Payout Threshold';
    if (score >= 90) tier = 'Tier 3 — 80% Coverage';
    else if (score >= 75) tier = 'Tier 2 — 50% Coverage';
    else if (score >= 60) tier = 'Tier 1 — 30% Coverage';

    let explanation = factors.length > 0 
        ? `${factors[0].label} elevated risk to ${score}/100.` 
        : `All parameters within safe operating ranges. Risk score ${score}/100.`;

    return { explanation, reasons, factors, confidence: Math.min(96, 62 + Math.round(score * 0.34)), tier, score };
}

function computeFraud(data) {
    const { rainfall = 0, aqi = 0, wind_speed = 0 } = data;
    const raw = typeof data.risk_score === 'number' ? data.risk_score : 0;
    const score = raw <= 1 ? raw : raw / 100;

    const envNorm = Math.min(1, ((Math.max(0, rainfall - 10) / 90) * 0.50) + ((Math.max(0, aqi - 100) / 300) * 0.30));
    const inconsistency = Math.abs(score - envNorm);
    const fraudScore = Math.min(0.92, Math.max(0.02, 0.04 + inconsistency * 0.25));

    if (fraudScore < 0.25) return { verdict: 'SAFE', badgeClass: 'fraud-verdict-safe', explanation: 'Readings are consistent. Claim verified.' };
    if (fraudScore < 0.60) return { verdict: 'REVIEW', badgeClass: 'fraud-verdict-review', explanation: 'Minor data discrepancy detected.' };
    return { verdict: 'BLOCKED', badgeClass: 'fraud-verdict-blocked', explanation: 'Significant anomaly: data inconsistent with sensors.' };
}

/* =====================================================================
   UI RENDERERS & ANIMATIONS
   ===================================================================== */

function renderAICard(data) {
    const res = renderExplanation(data);
    const textEl = document.getElementById('aiExplainText');
    const confEl = document.getElementById('aiConfidencePct');
    const factEl = document.getElementById('aiFactorsWrap');

    if (textEl) textEl.textContent = res.explanation;
    if (confEl) confEl.textContent = res.confidence + '%';
    if (factEl) {
        factEl.innerHTML = res.factors.map(f => `
            <div class="ai-factor ${f.severity}">
                <span class="ai-factor-label">${f.label}</span>
                <span class="ai-factor-val">+${f.contribution}% risk</span>
            </div>
        `).join('') || '<div class="ai-factor low">✅ All Clear</div>';
    }
}

function renderFraudCard(data) {
    const f = computeFraud(data);
    const verdictEl = document.getElementById('fraudVerdict');
    const explainEl = document.getElementById('fraudExplain');
    if (verdictEl) {
        verdictEl.textContent = f.verdict;
        verdictEl.className = `fraud-verdict ${f.badgeClass}`;
    }
    if (explainEl) explainEl.textContent = f.explanation;
}

function animateScoreBars() {
    document.querySelectorAll('.score-bar-fill, .factor-bar-fill').forEach(el => {
        const target = el.dataset.target ? `${el.dataset.target}%` : el.style.width;
        el.style.width = '0%';
        setTimeout(() => { el.style.width = target; }, 420);
    });
}

function initTooltips() {
    document.querySelectorAll('[data-tip]').forEach(el => {
        el.addEventListener('mouseenter', (e) => {
            const tip = document.createElement('div');
            tip.className = 'gg-tooltip';
            tip.textContent = el.dataset.tip;
            document.body.appendChild(tip);
            const r = el.getBoundingClientRect();
            tip.style.left = `${r.left + r.width / 2}px`;
            tip.style.top = `${r.top + window.scrollY - 8}px`;
            el._tip = tip;
        });
        el.addEventListener('mouseleave', () => { if (el._tip) { el._tip.remove(); el._tip = null; } });
    });
}

/**
 * Global Logout Function
 */
function logout() {
    sessionStorage.clear();
    window.location.replace('index.html');
}
