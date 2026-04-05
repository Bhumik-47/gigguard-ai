/**
 * GigGuard AI — Hackathon Stable script.js
 */

document.addEventListener("DOMContentLoaded", () => {
    // 1. --- AUTHENTICATION CHECK ---
    const auth = sessionStorage.getItem('gigguard_auth');
    const isLoginPage = window.location.pathname.includes('index.html') || window.location.pathname.endsWith('/');

    // If not on login page and not authenticated, go to login
    if (!isLoginPage && auth !== 'true') {
        window.location.replace('index.html');
        return; 
    }

    // 2. --- DASHBOARD INITIALIZATION ---
    // This only runs if we are on a page with the 'apiStatusText' element
    if (document.getElementById('apiStatusText')) {
        fetchAPI('/dashboard', (data) => {
            if (data && data.current_risk) {
                renderAICard(data.current_risk);
                renderFraudCard(data.current_risk);
            }
        }, () => {
            console.log("Running in Demo/Fallback Mode");
        });
    }

    // 3. --- UI EFFECTS ---
    animateScoreBars();
});

/* --- Core Engines --- */

async function fetchAPI(endpoint, onSuccess, onFallback) {
    try {
        // Pointing to local backend as per your original code
        const res = await fetch(`http://127.0.0.1:8000${endpoint}`);
        if (!res.ok) throw new Error('API Offline');
        const data = await res.json();
        onSuccess(data);
    } catch (err) {
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
    if (textEl) {
        const score = data.risk_score <= 1 ? Math.round(data.risk_score * 100) : data.risk_score;
        textEl.textContent = `AI Risk Engine evaluated disruption at ${score}/100.`;
    }
}

function renderFraudCard(data) {
    const verdictEl = document.getElementById('fraudVerdict');
    if (verdictEl) {
        verdictEl.textContent = "SAFE";
        verdictEl.className = "fraud-verdict fraud-verdict-safe";
    }
}

function logout() {
    sessionStorage.clear();
    window.location.replace('index.html');
}
