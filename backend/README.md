# FastAPI backend

The backend validates sensor input, stores raw readings in Firebase Realtime Database, runs the independent Python ML pipeline, persists predictions and alerts, and exposes data to the React dashboard.

## Configuration

From `backend/`, copy `.env.example` to `.env` and set the Firebase project, local service-account JSON path, trained model path, allowed frontend origins, and log level. Never commit `.env` or service-account files.

## Start the API

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive documentation is available at `http://localhost:8000/docs`; ReDoc is at `http://localhost:8000/redoc`.

## API endpoints

- `POST /predict` — validate and store a reading, run ML inference, persist the prediction, and create an alert for high-risk/anomalous results.
- `GET /sensor-data?device_id=esp32-001&limit=100` — list readings.
- `GET /devices` — list known devices and latest timestamps.
- `GET /latest?device_id=esp32-001` — return the latest reading for one device; omit `device_id` for one reading per device.
- `GET /alerts?device_id=esp32-001&limit=100` — list alerts.
- `GET /health` — report API, Firebase, and ML readiness.

## Test

```bash
python -m unittest discover -s tests -v
```

Endpoint tests use isolated Firebase and ML adapters and do not require production credentials. Live Firebase and ML readiness are reported by `/health`.
