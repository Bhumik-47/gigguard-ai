/**
 * GigGuard AI — Shared JavaScript Utilities
 * Updated for Vercel + Render Deployment
 */

// CHANGE THIS to your actual Render URL
const BASE_URL = "https://gigguard-ai.onrender.com"; 

/* =====================================================================
   ANIMATION UTILITIES
   ===================================================================== */

function animateNumber(el, target, opts = {}) {
    if (!el) return;
    const { prefix = '', suffix = '', duration = 1100, locale = 'en-IN', decimals = 0 } = opts;
    const startTime = performance.now();
  
    function tick(now) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
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

function animateScoreBars(delay = 420) {
    document.querySelectorAll('.score-bar-fill, .factor-bar-fill').forEach(el => {
      const target = el.dataset.target ? `${el.dataset.target}%` : el.style.width;
      el.style.width = '0%';
      setTimeout(() => { el.style.width = target; }, delay);
    });
}

/* =====================================================================
   API FETCH WITH FALLBACK
   ===================================================================== */

async function fetchAPI(endpoint, onSuccess, onFallback) {
    setApiStatus('loading');
    try {
      // Fetching from the live Render URL
      const res = await fetch(`${BASE_URL}${endpoint}`, {
          method: 'GET',
          headers: { 'Accept': 'application/json' }
      });
      
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      
      setApiStatus('live');
      onSuccess(data);
    } catch (err) {
      console.warn(`[GigGuard] API Connection Failed: ${err.message}. Using demo mode.`);
      setApiStatus('demo');
      if (onFallback) onFallback();
    }
}

function setApiStatus(state) {
    const text = document.getElementById('apiStatusText');
    if (!text) return;
    const map = { loading: 'Connecting...', live: 'Live Data ✅', demo: 'Demo Mode 💡', error: 'Offline' };
    text.textContent = map[state] || state;
}

/* =====================================================================
   UI RENDERING ENGINES
   ===================================================================== */

function renderAICard(data) {
    const result = renderExplanation(data);
    const textEl = document.getElementById('aiExplainText');
    const confEl = document.getElementById('aiConfidencePct');
    const factEl = document.getElementById('aiFactorsWrap');

    if (textEl) textEl.textContent = result.explanation;
    if (confEl) confEl.textContent = result.confidence + '%';
    
    if (factEl && result.factors) {
      factEl.innerHTML = result.factors.map(f => `
        <div class="ai-factor ${f.severity}">
          <span class="ai-factor-label">${f.label}</span>
          <span class="ai-factor-val">${f.value} &rarr; +${f.contribution}% risk</span>
        </div>
      `).join('') || `<div class="ai-factor low">All Clear</div>`;
    }
}

function renderFraudCard(data) {
    const f = computeFraud(data);
    const verdictEl = document.getElementById('fraudVerdict');
    const barEl = document.getElementById('fraudScoreBar');
    const labelEl = document.getElementById('fraudScoreLabel');

    if (verdictEl) {
        verdictEl.textContent = f.verdict;
        verdictEl.className = `verdict-badge verdict-${f.verdict}`;
    }
    if (barEl) {
        barEl.style.width = Math.round(f.score * 100) + '%';
    }
    if (labelEl) labelEl.textContent = f.score.toFixed(2);
}

// Reuse your logic functions (renderExplanation and computeFraud) from the original file here...
// [Keeping those the same as your provided code]

/* =====================================================================
   INITIALIZATION
   ===================================================================== */

document.addEventListener("DOMContentLoaded", () => {
    // 1. Check Auth (Standard security for your portal)
    if (!sessionStorage.getItem('gigguard_auth') && !window.location.href.includes('index.html')) {
        // window.location.href = 'index.html';
    }

    // 2. Fetch Data
    fetchAPI('/dashboard', (data) => {
        // SUCCESS PATH
        if (data.current_risk) {
            renderAICard(data.current_risk);
            renderFraudCard(data.current_risk);
        }
    }, () => {
        // FALLBACK PATH (Static data for demo if API fails)
        const demoData = { rainfall: 87, aqi: 312, wind_speed: 54, risk_score: 0.72 };
        renderAICard(demoData);
        renderFraudCard(demoData);
        animateScoreBars();
    });
});
