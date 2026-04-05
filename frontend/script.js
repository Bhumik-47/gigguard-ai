/**
 * GigGuard AI — Stable script.js
 */

document.addEventListener("DOMContentLoaded", () => {
    // 1. --- AUTHENTICATION CHECK ---
    const auth = sessionStorage.getItem('gigguard_auth');
    const path = window.location.pathname;
    
    // Safety check: Don't redirect if we are already on the login page
    const isLogin = path.includes('index.html') || path.endsWith('/') || path === '';

    if (!isLogin && auth !== 'true') {
        console.warn("Auth failed, redirecting...");
        window.location.replace('index.html');
        return; 
    }

    // 2. --- INITIALIZE DASHBOARD ---
    // Only runs if the elements exist on the page
    if (document.getElementById('apiStatusText')) {
        fetchAPI('/dashboard', (data) => {
            renderAICard(data.current_risk);
            renderFraudCard(data.current_risk);
        }, () => {
            console.log("Demo Mode Active");
        });
    }

    // 3. --- UI EFFECTS ---
    animateScoreBars();
});

/* --- Core Logic --- */

async function fetchAPI(endpoint, onSuccess, onFallback) {
    try {
        const res = await fetch(`http://127.0.0.1:8000${endpoint}`);
        if (!res.ok) throw new Error();
        const data = await res.json();
        onSuccess(data);
    } catch (e) {
        if (onFallback) onFallback();
    }
}

function animateScoreBars() {
    document.querySelectorAll('.score-bar-fill').forEach(el => {
        const target = el.dataset.target ? el.dataset.target + '%' : '70%';
        el.style.width = '0%';
        setTimeout(() => { el.style.width = target; }, 300);
    });
}

function renderAICard(data) {
    const textEl = document.getElementById('aiExplainText');
    if (textEl && data) {
        textEl.textContent = `Risk evaluated at ${Math.round(data.risk_score * 100)}/100.`;
    }
}

function renderFraudCard(data) {
    const verdictEl = document.getElementById('fraudVerdict');
    if (verdictEl) {
        verdictEl.textContent = "SAFE";
        verdictEl.className = "fraud-verdict fraud-verdict-safe";
    }
}
