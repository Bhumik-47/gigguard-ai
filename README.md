# GigGuard AI

Parametric insurance system designed to protect gig workers from income loss caused by environmental disruptions.

---

## Problem

Delivery partners (Swiggy, Zomato, Blinkit, etc.) rely on daily earnings. External conditions such as heavy rainfall, high pollution, and strong winds can reduce their working hours significantly.

In many cases, workers lose up to 20–30% of their income due to factors beyond their control, with no immediate financial protection.

---

## Solution

GigGuard AI provides a parametric insurance model that monitors environmental conditions and automatically triggers payouts when disruption thresholds are met.

The system removes the need for claim filing by using predefined triggers and real-time data to determine eligibility.

---

## Target User

* Platform-based delivery partners
* Urban regions (e.g., Delhi NCR)
* Workers dependent on daily or weekly income

---

## Pricing Model

| Plan          | Premium  | Coverage | Claims           |
| ------------- | -------- | -------- | ---------------- |
| Weekly Shield | ₹49/week | ₹2500    | Up to 2 per week |

The pricing model aligns with the weekly earning cycle of gig workers.

---

## Parametric Triggers

Payouts are triggered when environmental conditions exceed defined limits:

* Rainfall > 50 mm/hr
* AQI > 250
* Wind Speed > 45 km/h

---

## Risk Calculation

```id="y7nh5g"
risk_score = 0.5 × rainfall + 0.3 × AQI + 0.2 × wind_speed
```

Each parameter is normalized between safe and critical thresholds before computing the final score.

---

## Payout Logic

| Risk Score  | Payout          |
| ----------- | --------------- |
| < 0.60      | No payout       |
| 0.60 – 0.74 | 30% of coverage |
| 0.75 – 0.89 | 50% of coverage |
| ≥ 0.90      | 80% of coverage |

A small platform fee is deducted from the final payout.

---

## System Flow

User → Frontend → Backend API → Environmental Data → Risk Engine → Payout Engine → Result

---

## Key Features

* Risk assessment based on environmental conditions
* Parametric insurance model with predefined triggers
* Automatic payout calculation without manual claims
* Integration with external data sources (weather APIs)
* Dashboard for monitoring risk and payouts

---

## Tech Stack

* Frontend: HTML, CSS
* Backend: FastAPI (Python)
* External APIs: OpenWeatherMap
* Data Processing: Python services

---

## Project Structure

```
gigguard-ai/
├── backend/
│   ├── main.py
│   ├── risk_engine.py
│   ├── payout_engine.py
│   ├── data_service.py
│   ├── requirements.txt
│
├── frontend/
│   ├── index.html
│   ├── risk-monitor.html
│   ├── payout.html
│   ├── style.css
```

---

## Running the Project

```
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

Access API at: https://gigguard-ai-three.vercel.app/

---

## API Endpoints

* `/dashboard` → Worker dashboard data
* `/risk` → Current environmental risk
* `/simulate` → Random disruption scenario
* `/calculate` → Custom risk and payout

---

## Design Considerations

* Focus strictly on income protection (no health, vehicle, or life coverage)
* Weekly pricing model aligned with gig economy patterns
* Simple, automated workflow to reduce friction for workers

---

## Future Scope

* Real-time AQI integration
* Location-based risk personalization
* Mobile application interface
* Integration with gig platforms for onboarding

---
