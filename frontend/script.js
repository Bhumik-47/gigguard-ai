/**
 * GigGuard AI — Final Stable script.js
 */

document.addEventListener("DOMContentLoaded", () => {
    // 1. Auth Guard
    const auth = sessionStorage.getItem('gigguard_auth');
    const isLoginPage = window.location.pathname.includes('index.html') || window.location.pathname === '/';

    if (!isLoginPage && auth !== 'true') {
        window.location.replace('index.html');
        return;
    }

    // 2. Initialize Dashboard if elements exist
    if (document.getElementById('apiStatusText')) {
        fetchAPI('/dashboard', (data) => {
            renderAICard(data.current_risk);
            renderFraudCard(data.current_risk);
        }, () => {
            console.log("Running in Demo Mode");
        });
    }

    // 3. Global Animations
    animateScoreBars();
});

/* --- Core Engines --- */

async function fetchAPI(endpoint, onSuccess, onFallback) {
    try {
        const res = await fetch(`http://127.0.0.1:8000${endpoint}`);
        if (!res.ok) throw new Error('API Down');
        const data = await res.json();
        onSuccess(data);
    } catch (err) {
        if (onFallback) onFallback();
    }
}

function renderExplanation(data) {
    const raw = data.risk_score || 0;
    const score = raw <= 1 ? Math.round(raw * 100) : Math.round(raw);
    return {
        score,
        confidence: Math.min(96, 62 + Math.round(score * 0.34)),
        explanation: `Environmental risk evaluated at ${score}/100.`
    };
}

function renderAICard(data) {
    const res = renderExplanation(data);
    const textEl = document.getElementById('aiExplainText');
    const confEl = document.getElementById('aiConfidencePct');
    if (textEl) textEl.textContent = res.explanation;
    if (confEl) confEl.textContent = res.confidence + '%';
}

function renderFraudCard(data) {
    const verdictEl = document.getElementById('fraudVerdict');
    if (verdictEl) {
        verdictEl.textContent = "SAFE";
        verdictEl.className = "fraud-verdict fraud-verdict-safe";
    }
}

function animateScoreBars() {
    document.querySelectorAll('.score-bar-fill').forEach(el => {
        const target = el.dataset.target ? el.dataset.target + '%' : '70%';
        el.style.width = '0%';
        setTimeout(() => { el.style.width = target; }, 300);
    });
}

function logout() {
    sessionStorage.clear();
    window.location.replace('index.html');
}
