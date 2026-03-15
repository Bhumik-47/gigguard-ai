
# GigGuard AI — Backend

AI-powered parametric insurance backend for gig workers.  
Built with **Python + FastAPI**.

---

## Project Structure

```
backend/
├── main.py            # FastAPI app, all routes, CORS config
├── risk_engine.py     # Computes disruption risk score (0.0 – 1.0)
├── payout_engine.py   # Decides payout tier & calculates INR amount
├── data_service.py    # Mock worker/plan data + environmental scenarios
├── requirements.txt   # Python dependencies
└── README.md          # This file
```

---

## Quick Start

### 1. Create a virtual environment (recommended)

```bash
python -m venv venv
source venv/bin/activate        # macOS / Linux
venv\Scripts\activate           # Windows
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the development server

```bash
uvicorn main:app --reload
```

The API is now live at **http://127.0.0.1:8000**

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Health check |
| GET | `/dashboard` | All data for dashboard.html |
| GET | `/risk` | Live environmental conditions + risk score |
| GET | `/simulate` | Random disruption event + payout calculation |
| GET | `/calculate` | Custom calculation via query params |

### Interactive API docs (Swagger UI)

Open **http://127.0.0.1:8000/docs** in your browser to explore and test all endpoints.

---

## Example Requests

### GET /risk
```
curl http://127.0.0.1:8000/risk
```
```json
{
  "rainfall": 87.0,
  "aqi": 312.0,
  "wind_speed": 54.0,
  "risk_score": 0.7756,
  "risk_level": "HIGH",
  "payout_triggered": true,
  "payout": 1232.5,
  ...
}
```

### GET /simulate
```
curl http://127.0.0.1:8000/simulate
```
Returns a randomly chosen scenario — call multiple times to see different outputs.

### GET /calculate (custom inputs)
```
curl "http://127.0.0.1:8000/calculate?rainfall=70&aqi=280&wind_speed=20&coverage_cap=2500"
```
```json
{
  "rainfall": 70,
  "aqi": 280,
  "wind_speed": 20,
  "risk_score": 0.83,
  "risk_level": "HIGH",
  "payout_triggered": true,
  "payout_percentage": 0.5,
  "payout": 1237.5,
  "message": "Automatic payout triggered due to environmental disruption..."
}
```

---

## Risk Score Formula

```
risk_score = 0.50 × norm(rainfall)  +  0.30 × norm(AQI)  +  0.20 × norm(wind_speed)
```

Where `norm(x)` linearly maps each parameter between its safe baseline and critical ceiling:

| Parameter | Safe (0.0) | Critical (1.0) |
|-----------|-----------|---------------|
| Rainfall | 10 mm/hr | 100 mm/hr |
| AQI | 100 µg/m³ | 400 µg/m³ |
| Wind Speed | 20 km/h | 80 km/h |

---

## Payout Tiers

| Risk Score | Payout |
|-----------|--------|
| < 0.60 | 0 % (no payout) |
| 0.60 – 0.74 | 30 % of coverage cap |
| 0.75 – 0.89 | 50 % of coverage cap |
| ≥ 0.90 | 80 % of coverage cap |

A 1 % platform fee is deducted from the gross payout.

---

## Connecting the Frontend

In each frontend HTML file, replace the mock data fetch with:

```javascript
// dashboard.html
const res = await fetch("http://127.0.0.1:8000/dashboard");
const data = await res.json();

// risk-monitor.html
const res = await fetch("http://127.0.0.1:8000/risk");

// payout.html — simulator slider
const res = await fetch(
  `http://127.0.0.1:8000/calculate?rainfall=${r}&aqi=${a}&wind_speed=${w}`
);
```

CORS is already configured to allow all origins during development.

---

## Production Notes

- Replace `allow_origins=["*"]` in `main.py` with your frontend domain.
- Replace mock data in `data_service.py` with real DB queries and IMD/CPCB API calls.
- Add authentication (API keys / OAuth2) for worker-specific endpoints.
- Deploy with: `uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4`
