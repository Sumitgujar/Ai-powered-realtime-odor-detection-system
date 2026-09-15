# Dashboard — Local Setup Guide

This guide runs the complete **AI-Powered Real-Time Odor Detection System** locally: ML model, FastAPI backend, Firebase connection, and React dashboard.

## Prerequisites

Install:

- Git
- Python 3.10 or newer
- Node.js 18 or newer
- npm
- A Firebase project with Realtime Database enabled
- A Firebase service-account JSON file for the backend

Never commit `.env` files or the Firebase service-account JSON file.

## 1. Open the project

```bash
cd ai-powered-real-time-odor-detection-system
```

## 2. Configure and train the ML pipeline

```bash
cd ml
python -m venv .venv
```

Activate the environment.

### Linux/macOS

```bash
source .venv/bin/activate
```

### Windows PowerShell

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies and train the development model:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python generate_sample_data.py
python -m unittest discover -s tests -v
python -m src.train
```

Expected model file:

```text
ml/models/odor_pipeline.joblib
```

The sample dataset and its metrics are for simulated development testing only. Do not report them as real-world accuracy.

## 3. Configure Firebase and FastAPI

From the project root:

```bash
cd backend
python -m venv .venv
```

Activate the backend environment.

### Linux/macOS

```bash
source .venv/bin/activate
```

### Windows PowerShell

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Create the backend environment file.

### Linux/macOS

```bash
cp .env.example .env
```

### Windows PowerShell

```powershell
Copy-Item .env.example .env
```

Update `backend/.env`:

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

Apply `backend/firebase.database.rules.json` using the Firebase Console or Firebase CLI.

Test the backend:

```bash
python -m unittest discover -s tests -v
```

Start FastAPI:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Keep this terminal running.

Backend URLs:

- Health: `http://localhost:8000/health`
- Swagger: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

Verify health:

```bash
curl http://localhost:8000/health
```

Expected when Firebase and the ML model are ready:

```json
{
  "status": "healthy",
  "api": "ok",
  "firebase": "ok",
  "ml_model": "ok",
  "version": "0.2.0"
}
```

## 4. Configure the React dashboard

Open a second terminal:

```bash
cd ai-powered-real-time-odor-detection-system/frontend
```

Create the frontend environment file.

### Linux/macOS

```bash
cp .env.example .env
```

### Windows PowerShell

```powershell
Copy-Item .env.example .env
```

For FastAPI polling only, configure `frontend/.env` as follows:

```dotenv
VITE_API_BASE_URL=http://localhost:8000
VITE_POLL_INTERVAL_MS=5000

VITE_FIREBASE_API_KEY=
VITE_FIREBASE_AUTH_DOMAIN=
VITE_FIREBASE_DATABASE_URL=
VITE_FIREBASE_PROJECT_ID=
VITE_FIREBASE_APP_ID=
VITE_FIREBASE_USE_ANONYMOUS_AUTH=false
```

For direct Firebase realtime updates, also fill in the Firebase web values:

```dotenv
VITE_API_BASE_URL=http://localhost:8000
VITE_POLL_INTERVAL_MS=5000

VITE_FIREBASE_API_KEY=your-web-api-key
VITE_FIREBASE_AUTH_DOMAIN=your-project-id.firebaseapp.com
VITE_FIREBASE_DATABASE_URL=https://your-project-id-default-rtdb.firebaseio.com
VITE_FIREBASE_PROJECT_ID=your-project-id
VITE_FIREBASE_APP_ID=your-web-app-id
VITE_FIREBASE_USE_ANONYMOUS_AUTH=true
```

If anonymous authentication is enabled in the environment file, enable the Anonymous provider in Firebase Authentication. Firebase web configuration values identify the Firebase project; backend service-account credentials must never be placed in the frontend.

Install, verify, and build:

```bash
npm install
npm run typecheck
npm run verify:components
npm run build
```

Test the dashboard API contract while FastAPI is running:

```bash
API_BASE_URL=http://localhost:8000 npm run test:api
```

Windows PowerShell:

```powershell
$env:API_BASE_URL="http://localhost:8000"
npm run test:api
```

To test `/predict` as well, this creates one simulated test reading:

### Linux/macOS

```bash
API_BASE_URL=http://localhost:8000 TEST_PREDICT=true npm run test:api
```

### Windows PowerShell

```powershell
$env:API_BASE_URL="http://localhost:8000"
$env:TEST_PREDICT="true"
npm run test:api
```

Start the dashboard:

```bash
npm run dev
```

Open:

```text
http://localhost:5173
```

## 5. Optional simulated sensor stream

Open a third terminal and activate the backend Python environment:

```bash
cd ai-powered-real-time-odor-detection-system/backend
```

### Linux/macOS

```bash
source .venv/bin/activate
python simulator.py --count 100 --interval 2 --device-id simulator-001
```

### Windows PowerShell

```powershell
.venv\Scripts\Activate.ps1
python simulator.py --count 100 --interval 2 --device-id simulator-001
```

Every generated reading is marked as simulated.

## How live data reaches the dashboard

1. ESP32 devices or the simulator write sensor readings to Firebase.
2. FastAPI reads and stores sensor information, runs the trained model, and writes predictions and alerts.
3. The dashboard polls FastAPI every five seconds for health, sensor history, devices, latest readings, and alerts.
4. If Firebase web settings are configured, the dashboard also uses Realtime Database listeners for immediate sensor, prediction, and alert updates.
5. The dashboard never substitutes fake UI data. It shows loading, empty, degraded, or error states when services are unavailable.

## Troubleshooting

### FastAPI is unavailable

Confirm that it is running on port `8000`:

```bash
curl http://localhost:8000/health
```

### CORS error

Ensure `backend/.env` contains:

```dotenv
CORS_ORIGINS=http://localhost:5173
```

Restart FastAPI after changing `.env`.

### ML model unavailable

Confirm this file exists:

```text
ml/models/odor_pipeline.joblib
```

Then confirm `backend/.env` contains:

```dotenv
ML_MODEL_PATH=../ml/models/odor_pipeline.joblib
```

### Firebase unavailable

Verify the project ID, database URL, service-account path, Firebase Auth configuration, and Realtime Database rules.

### Dashboard build fails

Remove local dependencies and reinstall:

### Linux/macOS

```bash
rm -rf node_modules package-lock.json
npm install
npm run build
```

### Windows PowerShell

```powershell
Remove-Item -Recurse -Force node_modules
Remove-Item -Force package-lock.json -ErrorAction SilentlyContinue
npm install
npm run build
```

### Blank dashboard

Open browser developer tools and check the Console and Network tabs. Confirm requests to `http://localhost:8000` return HTTP 200 and that the frontend `.env` values are correct. Restart Vite after changing environment variables.
