/**
 * GigGuard AI — Final Stable script.js
 */

document.addEventListener("DOMContentLoaded", () => {
    // 1. --- AUTHENTICATION CHECK ---
    const auth = sessionStorage.getItem('gigguard_auth');
    const path = window.location.pathname;

    // Only redirect if we are NOT on the login page (index.html)
    if (!path.includes('index.html') && path !== '/' && path !== '') {
        if (auth !== 'true') {
            window.location.replace('index.html');
            return; 
        }
    }

    // 2. --- DASHBOARD LOADING ---
    // Wrapped in a check to prevent errors on pages without these IDs
    const statusText = document.getElementById('apiStatusText');
    if (statusText) {
        fetchAPI('/dashboard', (data) => {
            if (data && data.current_risk) {
                renderAICard(data.current_risk);
                renderFraudCard(data.current_risk);
            }
        }, () => {
            console.log("Backend offline: Running Demo Mode");
        });
    }

    // 3. --- UI INITIALIZATION ---
    animateScoreBars();
});

/* --- Global Utilities --- */

async function fetchAPI(endpoint, onSuccess, onFallback) {
    try {
        // Points to your local python backend
        const res = await fetch(`http://127.0.0.1:8000${endpoint}`);
        if (!res.ok) throw new Error('API Error');
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
    if (textEl) textEl.textContent = `Risk score evaluated at ${Math.round(data.risk_score * 100)}/100.`;
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
