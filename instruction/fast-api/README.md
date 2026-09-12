# FastAPI Backend Instructions

These instructions apply to the `backend/` folder of the **AI-Powered Real-Time Odor Detection System**.

## 1. Open the backend folder

```bash
cd ai-powered-real-time-odor-detection-system/backend
```

## 2. Create and activate a virtual environment

### Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Windows PowerShell

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

## 3. Install dependencies

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## 4. Configure environment variables

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

Never commit `.env` or the Firebase service-account JSON file.

## 5. Train the ML model when needed

Run this if `ml/models/odor_pipeline.joblib` does not exist:

```bash
cd ../ml
python generate_sample_data.py
python -m src.train
cd ../backend
```

Metrics generated from the sample dataset are simulated development metrics, not real-world accuracy.

## 6. Run all backend tests

```bash
python -m unittest discover -s tests -v
```

All tests should pass before starting frontend integration.

## 7. Start FastAPI

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Available documentation:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## API requests

### Health

```bash
curl http://localhost:8000/health
```

Expected when all dependencies are ready:

```json
{
  "status": "healthy",
  "api": "ok",
  "firebase": "ok",
  "ml_model": "ok",
  "version": "0.2.0"
}
```

### Prediction

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "esp32-001",
    "timestamp": "2026-09-12T05:30:00Z",
    "latitude": 18.5204,
    "longitude": 73.8567,
    "bme_gas": 23000,
    "mq135": 740,
    "mq136": 410,
    "mq3": 250,
    "temperature": 27.4,
    "humidity": 58,
    "pressure": 1007.5,
    "is_simulated": true
  }'
```

Expected response structure:

```json
{
  "odor_class": "smoke",
  "intensity": "high",
  "anomaly_status": false,
  "confidence": 0.91,
  "prediction_risk": "high",
  "timestamp": "2026-09-12T05:30:00Z",
  "device_id": "esp32-001",
  "reading_id": "esp32-001/firebase-reading-key",
  "prediction_id": "esp32-001/firebase-prediction-key"
}
```

Actual prediction values depend on the trained model.

### Sensor data

```bash
curl "http://localhost:8000/sensor-data?device_id=esp32-001&limit=10"
```

### Devices

```bash
curl http://localhost:8000/devices
```

### Latest reading for one device

```bash
curl "http://localhost:8000/latest?device_id=esp32-001"
```

Latest reading for every device:

```bash
curl http://localhost:8000/latest
```

### Alerts

```bash
curl "http://localhost:8000/alerts?device_id=esp32-001&limit=10"
```

## Common errors

### Firebase unavailable

Check `FIREBASE_PROJECT_ID`, `FIREBASE_DATABASE_URL`, and `FIREBASE_CREDENTIALS_PATH` in `.env`. Confirm that the credentials file exists and is not committed to Git.

### ML model unavailable

Train the model and confirm that `ML_MODEL_PATH` points to `ml/models/odor_pipeline.joblib`.

### Validation error

FastAPI returns HTTP `422` when a required field is missing, a timestamp has no timezone, or a sensor value is outside its accepted range.

### CORS error

Add the exact React origin to `CORS_ORIGINS`, for example:

```dotenv
CORS_ORIGINS=http://localhost:5173
```
