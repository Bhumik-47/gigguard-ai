/**
 * GigGuard AI — Shared JavaScript Utilities
 * Reusable across all pages: dashboard, risk-monitor, payout
 */

/* =====================================================================
   ANIMATION UTILITIES
   ===================================================================== */

/**
 * Animate a number counting up from 0 to target.
 * @param {HTMLElement} el - DOM element to update
 * @param {number} target - Final numeric value
 * @param {object} opts - { prefix, suffix, duration, locale, decimals }
 */
// Add this to the TOP of script.js
// TOP OF script.js
(function() {
    const auth = sessionStorage.getItem('gigguard_auth');
    console.log("Checking Auth Status:", auth); // Debugging line

    if (auth !== 'true') {
        console.warn("Auth failed, redirecting to login...");
        window.location.replace('index.html');
    }
})();
function animateNumber(el, target, opts = {}) {
    const { prefix = '', suffix = '', duration = 1100, locale = 'en-IN', decimals = 0 } = opts;
    const startTime = performance.now();
  
    function tick(now) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // Ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = target * eased;
  
      const display = decimals > 0
        ? current.toFixed(decimals)
        : Math.round(current).toLocaleString(locale);
  
      el.textContent = prefix + display + suffix;
  
      if (progress < 1) requestAnimationFrame(tick);
      else el.textContent = prefix + (decimals > 0 ? target.toFixed(decimals) : target.toLocaleString(locale)) + suffix;
    }
  
    requestAnimationFrame(tick);
  }
  
  /**
   * Animate all .score-bar-fill and .factor-bar-fill from 0 to their target.
   * Uses data-target attribute (raw number) or falls back to inline style width.
   * @param {number} delay - ms before starting
   */
  function animateScoreBars(delay = 420) {
    document.querySelectorAll('.score-bar-fill, .factor-bar-fill').forEach(el => {
      const target = el.dataset.target ? `${el.dataset.target}%` : el.style.width;
      el.style.width = '0%';
      setTimeout(() => { el.style.width = target; }, delay);
    });
  }
  
  /* =====================================================================
     RISK UI HELPERS
     ===================================================================== */
  
  /**
   * Return colour/class metadata based on a 0–100 risk score.
   */
  function getRiskUI(score) {
    if (score >= 70) return { level: 'HIGH', color: 'var(--red)', barClass: 'fill-red', badgeClass: 'badge-red', icon: '🔴', glow: 'rgba(255,75,92,0.2)' };
    if (score >= 40) return { level: 'MEDIUM', color: 'var(--amber)', barClass: 'fill-amber', badgeClass: 'badge-amber', icon: '🟡', glow: 'rgba(245,165,35,0.2)' };
    return { level: 'LOW', color: 'var(--green)', barClass: 'fill-green', badgeClass: 'badge-green', icon: '🟢', glow: 'rgba(34,217,122,0.2)' };
  }
  
  /* =====================================================================
     AI EXPLANATION ENGINE
     ===================================================================== */
  
  /**
   * Generate a human-readable AI explanation from live data.
   * @param {object} data - API response (rainfall, aqi, wind_speed, risk_score 0-1, payout, payout_triggered)
   * @returns {{ explanation, reasons, factors, confidence, tier, score }}
   */
  function renderExplanation(data) {
    const { rainfall = 0, aqi = 0, wind_speed = 0, payout = 0, payout_triggered = false } = data;
    // risk_score may be 0-1 (API) or already 0-100
    const raw = typeof data.risk_score === 'number' ? data.risk_score : 0;
    const score = raw <= 1 ? Math.round(raw * 100) : Math.round(raw);
  
    const factors = [];
    const reasons = [];
  
    if (rainfall >= 50) {
      const contrib = Math.min(42, Math.round((rainfall - 50) / 80 * 35 + 12));
      factors.push({ label: '🌧 Rainfall', value: `${rainfall} mm/hr`, severity: rainfall >= 80 ? 'critical' : 'high', contribution: contrib });
      reasons.push(`Rainfall ${rainfall}mm/hr exceeds safe threshold (50mm/hr) — +${contrib}% risk contribution`);
    }
    if (aqi >= 250) {
      const contrib = Math.min(28, Math.round((aqi - 250) / 200 * 20 + 8));
      factors.push({ label: '💨 Air Quality', value: `AQI ${aqi} µg/m³`, severity: aqi >= 300 ? 'critical' : 'high', contribution: contrib });
      reasons.push(`AQI ${aqi}µg/m³ classified Hazardous (CPCB scale >300) — +${contrib}% disruption index`);
    }
    if (wind_speed >= 45) {
      const contrib = Math.min(18, Math.round((wind_speed - 45) / 45 * 12 + 5));
      factors.push({ label: '🌬 Wind Speed', value: `${wind_speed} km/h`, severity: wind_speed >= 65 ? 'critical' : 'elevated', contribution: contrib });
      reasons.push(`Wind ${wind_speed}km/h exceeds safe operational limit (45km/h) — control & visibility risk`);
    }
  
    // Tier label (matches payout engine tiers: <0.60=0%, <0.75=30%, <0.90=50%, ≥0.90=80%)
    let tier = 'Below Payout Threshold';
    const rs = raw <= 1 ? raw : raw / 100;
    if (rs >= 0.90) tier = 'Tier 3 — 80% Coverage';
    else if (rs >= 0.75) tier = 'Tier 2 — 50% Coverage';
    else if (rs >= 0.60) tier = 'Tier 1 — 30% Coverage';
  
    let explanation;
    if (factors.length >= 2) {
      const f1 = factors[0].label.replace(/[^\w\s]/g, '').trim();
      const f2 = factors[1].label.replace(/[^\w\s]/g, '').trim();
      explanation = `${f1} (${factors[0].value}) combined with ${f2} (${factors[1].value}) raised disruption probability to ${score}/100, satisfying ${tier} payout criteria${payout_triggered ? ` — ₹${Math.round(payout).toLocaleString('en-IN')} initiated automatically` : ''}.`;
    } else if (factors.length === 1) {
      explanation = `${factors[0].label} at ${factors[0].value} elevated disruption risk to ${score}/100. ${payout_triggered ? `${tier} — ₹${Math.round(payout).toLocaleString('en-IN')} payout automatically initiated.` : 'Approaching payout threshold — monitoring continues.'}`;
    } else {
      explanation = `All environmental parameters are within safe operating ranges. Risk score ${score}/100 is below the payout activation threshold (60). Coverage is active and real-time monitoring is running.`;
    }
  
    const confidence = Math.min(96, 62 + Math.round(score * 0.34));
    return { explanation, reasons, factors, confidence, tier, score };
  }
  
  /* =====================================================================
     FRAUD INTELLIGENCE ENGINE
     ===================================================================== */
  
  /**
   * Compute a fraud score from environmental consistency.
   * Returns verdict SAFE / REVIEW / BLOCKED and explanation.
   */
  function computeFraud(data) {
    const { rainfall = 0, aqi = 0, wind_speed = 0 } = data;
    const raw = typeof data.risk_score === 'number' ? data.risk_score : 0;
    const score = raw <= 1 ? raw : raw / 100;
  
    // Build expected risk from raw env values independently
    const envNorm = Math.min(1,
      ((Math.max(0, rainfall - 10) / 90) * 0.50) +
      ((Math.max(0, aqi - 100) / 300) * 0.30) +
      ((Math.max(0, wind_speed - 20) / 60) * 0.20)
    );
    const inconsistency = Math.abs(score - envNorm);
  
    let fraudScore = 0.04 + inconsistency * 0.25;
    fraudScore = Math.min(0.92, Math.max(0.02, parseFloat(fraudScore.toFixed(3))));
  
    let verdict, color, bgColor, borderColor, explanation, badgeClass;
    if (fraudScore < 0.25) {
      verdict = 'SAFE'; color = 'var(--green)'; bgColor = 'var(--green-dim)';
      borderColor = 'rgba(34,217,122,0.25)'; badgeClass = 'fraud-verdict-safe';
      explanation = 'Environmental readings from IMD + CPCB are internally consistent with the risk assessment. Claim verified.';
    } else if (fraudScore < 0.60) {
      verdict = 'REVIEW'; color = 'var(--amber)'; bgColor = 'rgba(245,165,35,0.10)';
      borderColor = 'rgba(245,165,35,0.25)'; badgeClass = 'fraud-verdict-review';
      explanation = 'Minor data discrepancy detected between sensor readings. Flagged for automated secondary verification.';
    } else {
      verdict = 'BLOCKED'; color = 'var(--red)'; bgColor = 'var(--red-dim)';
      borderColor = 'rgba(255,75,92,0.25)'; badgeClass = 'fraud-verdict-blocked';
      explanation = 'Significant anomaly: risk score inconsistent with third-party environmental sensor data. Claim held for manual review.';
    }
  
    return { score: fraudScore, verdict, color, bgColor, borderColor, explanation, badgeClass };
  }
  
  /* =====================================================================
     API STATUS INDICATOR
     ===================================================================== */
  
  function setApiStatus(state) {
    const dot = document.getElementById('apiStatusDot');
    const text = document.getElementById('apiStatusText');
    const wrap = document.getElementById('apiStatusWrap');
    if (!dot) return;
  
    dot.className = `api-dot ${state}`;
    if (wrap) wrap.className = `nav-status api-indicator ${state}`;
    const map = { loading: 'Connecting…', live: 'Live Data', error: 'Demo Mode', demo: 'Demo Mode' };
    if (text) text.textContent = map[state] || state;
  }
  
  /* =====================================================================
     SHIMMER HELPERS
     ===================================================================== */
  
  function showShimmer(selector) {
    document.querySelectorAll(selector).forEach(el => el.classList.add('is-shimmer'));
  }
  function hideShimmer(selector) {
    document.querySelectorAll(selector).forEach(el => el.classList.remove('is-shimmer'));
  }
  
  /* =====================================================================
     GENERIC API FETCH WITH FALLBACK
     ===================================================================== */
  
  /**
   * Fetch from backend (localhost:8000) with graceful demo fallback.
   * @param {string} endpoint - e.g. '/dashboard'
   * @param {function} onSuccess - called with parsed JSON
   * @param {function} onFallback - called when fetch fails (use demo data)
   */
  async function fetchAPI(endpoint, onSuccess, onFallback) {
    setApiStatus('loading');
    try {
      const res = await fetch(`http://127.0.0.1:8000${endpoint}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setApiStatus('live');
      onSuccess(data);
    } catch (err) {
      console.warn(`[GigGuard] API unavailable (${endpoint}):`, err.message, '— using demo data');
      setApiStatus('demo');
      if (onFallback) onFallback();
    }
  }
  
  /* =====================================================================
     TOOLTIP ENGINE
     ===================================================================== */
  
  function initTooltips() {
    document.querySelectorAll('[data-tip]').forEach(el => {
      let tip = null;
  
      el.addEventListener('mouseenter', () => {
        tip = document.createElement('div');
        tip.className = 'gg-tooltip';
        tip.textContent = el.dataset.tip;
        document.body.appendChild(tip);
        const r = el.getBoundingClientRect();
        tip.style.left = (r.left + r.width / 2) + 'px';
        tip.style.top = (r.top + window.scrollY - 8) + 'px';
      });
  
      el.addEventListener('mouseleave', () => {
        if (tip) { tip.remove(); tip = null; }
      });
    });
  }
  
  /* =====================================================================
     REFRESH BUTTON SPIN
     ===================================================================== */
  
  function setRefreshing(btn, spinning) {
    if (!btn) return;
    btn.classList.toggle('spinning', spinning);
    btn.disabled = spinning;
  }
  
  /* =====================================================================
     RENDER HELPERS (shared building blocks)
     ===================================================================== */
  
  /**
   * Inject AI Explanation card content.
   * Expects elements: #aiExplainText, #aiConfidencePct, #aiFactorsWrap, #aiMeta
   */
  function renderAICard(data) {
    const result = renderExplanation(data);
  
    const textEl = document.getElementById('aiExplainText');
    const confEl = document.getElementById('aiConfidencePct');
    const factEl = document.getElementById('aiFactorsWrap');
    const tierEl = document.getElementById('aiTierLabel');
  
    if (textEl) textEl.textContent = result.explanation;
    if (confEl) confEl.textContent = result.confidence + '%';
    if (tierEl) tierEl.textContent = result.tier;
  
    if (factEl) {
      factEl.innerHTML = result.factors.map(f => `
        <div class="ai-factor ${f.severity}">
          <span class="ai-factor-label">${f.label}</span>
          <span class="ai-factor-val">${f.value} &rarr; +${f.contribution}% risk</span>
        </div>
      `).join('') + (result.factors.length === 0
        ? `<div class="ai-factor low"><span class="ai-factor-label">✅ All Clear</span><span class="ai-factor-val">No thresholds breached</span></div>`
        : '');
    }
  
    // Reasons list
    const reasonsEl = document.getElementById('aiReasonsList');
    if (reasonsEl) {
      reasonsEl.innerHTML = result.reasons.map(r => `<li>${r}</li>`).join('') ||
        '<li>All environmental readings within normal operating parameters</li>';
    }
  }
  
  /**
   * Inject Fraud Intelligence card content.
   * Expects elements: #fraudVerdict, #fraudScoreBar, #fraudScoreLabel, #fraudExplain
   */
  function renderFraudCard(data) {
    const f = computeFraud(data);
  
    const verdictEl = document.getElementById('fraudVerdict');
    const barEl = document.getElementById('fraudScoreBar');
    const labelEl = document.getElementById('fraudScoreLabel');
    const explainEl = document.getElementById('fraudExplain');
  
    if (verdictEl) {
      verdictEl.textContent = f.verdict;
      verdictEl.className = `fraud-verdict ${f.badgeClass}`;
    }
    if (barEl) {
      barEl.className = `score-bar-fill ${f.score < 0.25 ? 'fill-green' : f.score < 0.60 ? 'fill-amber' : 'fill-red'}`;
      barEl.style.width = '0%';
      setTimeout(() => { barEl.style.width = Math.round(f.score * 100) + '%'; }, 500);
    }
    if (labelEl) {
      labelEl.textContent = f.score.toFixed(2) + ' / 1.00';
      labelEl.style.color = f.color;
    }
    if (explainEl) explainEl.textContent = f.explanation;
  }
  document.addEventListener("DOMContentLoaded", () => {
    fetchAPI('/dashboard', (data) => {
  
      console.log("API DATA:", data);
  
      // Example updates (adjust IDs if needed)
      document.getElementById("apiStatusText").innerText = "Live Data ✅";
  
      renderAICard(data.current_risk);
      renderFraudCard(data.current_risk);
  
    }, () => {
      console.log("Using demo fallback");
    });
  });
