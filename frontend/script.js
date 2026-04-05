/**
 * GigGuard AI — Stable Hackathon Version
 */

document.addEventListener("DOMContentLoaded", () => {
    // 1. --- AUTH CHECK ---
    const auth = sessionStorage.getItem('gigguard_auth');
    const path = window.location.pathname;
    const isLogin = path.includes('index.html') || path.endsWith('/') || path === '';

    // If on a dashboard page without being logged in, redirect to index
    if (!isLogin && auth !== 'true') {
        window.location.replace('index.html');
        return; 
    }

    // 2. --- DASHBOARD LOADING ---
    // Only attempts to fetch if the UI elements exist
    if (document.getElementById('apiStatusText')) {
        fetchAPI('/dashboard', (data) => {
            if (data && data.current_risk) {
                updateUI(data.current_risk);
            }
        }, () => {
            console.log("Running in Demo Mode (Backend Offline)");
        });
    }

    // 3. --- UI INITIALIZATION ---
    runAnimations();
});

/* --- Core Functions --- */

async function fetchAPI(endpoint, onSuccess, onFallback) {
    try {
        // Change this URL if you deploy your backend to a real server
        const res = await fetch(`http://127.0.0.1:8000${endpoint}`);
        if (!res.ok) throw new Error('API Error');
        const data = await res.json();
        onSuccess(data);
    } catch (err) {
        if (onFallback) onFallback();
    }
}

function updateUI(riskData) {
    const textEl = document.getElementById('aiExplainText');
    if (textEl) {
        const score = riskData.risk_score <= 1 ? Math.round(riskData.risk_score * 100) : riskData.risk_score;
        textEl.textContent = `AI Risk Engine evaluated disruption at ${score}/100.`;
    }
    
    const verdictEl = document.getElementById('fraudVerdict');
    if (verdictEl) {
        verdictEl.textContent = "SAFE";
        verdictEl.className = "fraud-verdict fraud-verdict-safe";
    }
}

function runAnimations() {
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
