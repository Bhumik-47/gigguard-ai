UPDATED DEPLOY LINK : https://gigguard-ai-qv7z-e8teghx5v-bhumikkannu-3503s-projects.vercel.app/
 
 GigGuard AI

Real-time AI-powered parametric insurance system for gig workers that automatically calculates disruption risk and triggers payouts based on live environmental conditions.

---

## Problem

Gig workers such as delivery partners are highly vulnerable to environmental disruptions like heavy rainfall, poor air quality, and extreme weather conditions. These directly impact their ability to work and earn.

Traditional insurance systems:
- Require manual claims
- Are slow and delayed
- Do not operate in real time

---

## Solution

GigGuard AI introduces a parametric insurance model where:

- Environmental data is monitored in real time  
- Risk is computed instantly  
- Payouts are triggered automatically  
- No manual claim process is required  

---

## Features

### Real-Time Environmental Data
- Integrated with OpenWeatherMap API  
- Fetches:
  - Rainfall (mm/hr)
  - Wind speed (km/h)
  - Weather conditions  
- Converts live data into risk inputs  

---

### AI-Based Risk Engine

Risk score computed using weighted model:

- Rainfall → 50%  
- AQI (derived) → 30%  
- Wind Speed → 20%  

Outputs:
- Risk Score (0–1)
- Risk Level: LOW / MEDIUM / HIGH / CRITICAL  

---

### Parametric Payout Engine

| Risk Score | Payout |
|------------|--------|
| < 0.60 | 0% |
| 0.60–0.75 | 30% |
| 0.75–0.90 | 50% |
| ≥ 0.90 | 80% |

- Instant payout calculation  
- No claim required  

---

### AI Explanation Layer

- Explains payout decisions  
- Identifies dominant risk factors  
- Improves transparency and trust  

---

### Dashboard

- Worker profile and plan details  
- Live environmental data  
- Risk score visualization  
- Payout status tracking  

---

## How It Works

1. Fetch real-time environmental data  
2. Normalize values  
3. Compute weighted risk score  
4. Determine payout tier  
5. Trigger payout  
6. Display results on dashboard  

---

## Tech Stack

### Backend
- FastAPI (Python)  
- Risk Engine  
- Payout Engine  

### Frontend
- HTML  
- CSS  
- JavaScript  

### APIs
- OpenWeatherMap  

---

## API Endpoints

- `/dashboard` → Worker + plan + risk data  
- `/risk` → Environmental risk details  
- `/simulate` → Scenario simulation  
- `/calculate` → Custom risk calculation  

---

## Repository

https://github.com/Bhumik-47/gigguard-ai.git

---

## Run Locally

```bash
git clone https://github.com/Bhumik-47/gigguard-ai.git
cd gigguard-ai/backend
pip install fastapi uvicorn requests
python3 -m uvicorn main:app --reload

Open:https://gigguard-ai-qv7z-e8teghx5v-bhumikkannu-3503s-projects.vercel.app/
---
##Future Scope
1)Real AQI API integration
2)ML-based predictive risk modeling
3)Mobile application
4)Payment gateway integration

------------------------------------------------------------
