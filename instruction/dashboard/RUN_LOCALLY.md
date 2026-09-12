# Run the Dashboard Locally

Use three terminals so the backend, frontend, and optional simulator can run at the same time.

## Before starting

Confirm that the project contains:

```text
ai-powered-real-time-odor-detection-system/
├── backend/
├── frontend/
├── ml/
└── firmware/
```

Install Python 3.10+, Node.js 18+, npm, and Git.

## First-time setup

### A. Train the ML model

```bash
cd ai-powered-real-time-odor-detection-system/ml
python -m venv .venv
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Then run:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python generate_sample_data.py
python -m unittest discover -s tests -v
python -m src.train
```

Confirm that this file was created:

```text
ml/models/odor_pipeline.joblib
```

### B. Configure the backend

```bash
cd ../backend
python -m venv .venv
```

Linux/macOS:

```bash
source .venv/bin/activate
cp .env.example .env
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
Copy-Item .env.example .env
```

Install dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Set these values in `backend/.env`:

```dotenv
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_DATABASE_URL=https://your-project-id-default-rtdb.firebaseio.com
FIREBASE_CREDENTIALS_PATH=/absolute/path/to/firebase-service-account.json
FIREBASE_SENSOR_DATA_PATH=sensor_readings
FIREBASE_PREDICTIONS_PATH=predictions
FIREBASE_ALERTS_PATH=alerts
ML_MODEL_PATH=../ml/models/odor_pipeline.joblib
CORS_ORIGINS=http://localhost:5173
LOG_LEVEL=INFO
```

Do not commit `.env` or the service-account JSON file.

### C. Configure the dashboard

```bash
cd ../frontend
```

Linux/macOS:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

For FastAPI polling, use:

```dotenv
VITE_API_BASE_URL=http://localhost:8000
VITE_POLL_INTERVAL_MS=5000
VITE_FIREBASE_USE_ANONYMOUS_AUTH=false
```

Install and validate:

```bash
npm install
npm run typecheck
npm run verify:components
npm run build
```

## Start the system

### Terminal 1 — FastAPI

```bash
cd ai-powered-real-time-odor-detection-system/backend
```

Activate `.venv`, then run:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Verify:

```bash
curl http://localhost:8000/health
```

Open API documentation:

```text
http://localhost:8000/docs
```

### Terminal 2 — React dashboard

```bash
cd ai-powered-real-time-odor-detection-system/frontend
npm run dev
```

Open:

```text
http://localhost:5173
```

### Terminal 3 — Optional simulator

```bash
cd ai-powered-real-time-odor-detection-system/backend
```

Activate `.venv`, then run:

```bash
python simulator.py --count 100 --interval 2 --device-id simulator-001
```

## Verify API integration

From `frontend/`:

Linux/macOS:

```bash
API_BASE_URL=http://localhost:8000 npm run test:api
```

Windows PowerShell:

```powershell
$env:API_BASE_URL="http://localhost:8000"
npm run test:api
```

Test `/predict` too:

Linux/macOS:

```bash
API_BASE_URL=http://localhost:8000 TEST_PREDICT=true npm run test:api
```

Windows PowerShell:

```powershell
$env:API_BASE_URL="http://localhost:8000"
$env:TEST_PREDICT="true"
npm run test:api
```

## Expected local services

| Service | Address |
| --- | --- |
| React dashboard | `http://localhost:5173` |
| FastAPI | `http://localhost:8000` |
| API documentation | `http://localhost:8000/docs` |
| Health check | `http://localhost:8000/health` |

## If something fails

1. Check that FastAPI health returns HTTP 200.
2. Check that `ml/models/odor_pipeline.joblib` exists.
3. Verify the Firebase URL and service-account path.
4. Restart FastAPI after changing `backend/.env`.
5. Restart Vite after changing `frontend/.env`.
6. Check the browser Console and Network tabs.
7. Confirm `CORS_ORIGINS=http://localhost:5173` in `backend/.env`.
8. Run `npm run build` and fix any TypeScript errors before continuing.
