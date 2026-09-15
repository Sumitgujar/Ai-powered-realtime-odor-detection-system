# Hardware ESP — 7-Step Verification Guide

Use this guide to verify the physical pipeline:

```text
ESP32 sensors → Firebase → FastAPI/ML → Firebase predictions → React dashboard
```

## Prerequisites

- ESP32 DevKit
- BME688
- MQ-135, MQ-136 and MQ-3
- Voltage dividers for MQ analog outputs
- Optional GPS module
- Firebase Realtime Database and Email/Password Authentication
- Trained model at `ml/models/odor_pipeline.joblib`
- FastAPI and React dependencies installed

> Never connect a 5 V MQ analog output directly to an ESP32 ADC pin.

## Step 1 — Flash the ESP32 and open Serial Monitor

```bash
cd ai-powered-real-time-odor-detection-system/firmware
cp include/config.example.h include/config.h
```

Windows PowerShell:

```powershell
Copy-Item include/config.example.h include/config.h
```

Configure `include/config.h`:

```cpp
#define WIFI_SSID "YOUR_WIFI_NAME"
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"
#define FIREBASE_API_KEY "YOUR_FIREBASE_WEB_API_KEY"
#define FIREBASE_DATABASE_URL "https://YOUR_PROJECT_ID-default-rtdb.firebaseio.com"
#define FIREBASE_USER_EMAIL "device-account@example.com"
#define FIREBASE_USER_PASSWORD "DEVICE_ACCOUNT_PASSWORD"
#define GPS_ENABLED false
#define DEFAULT_LATITUDE 18.5204
#define DEFAULT_LONGITUDE 73.8567
```

Build, upload and monitor:

```bash
pio pkg install
pio test -e native
pio run
pio run --target upload
pio device monitor --baud 115200
```

Expected boot messages:

```text
[boot] AI odor sensor node starting
[boot] Device ID: odor-node-...
[sensor] BME688 initialized
[wifi] Connecting to ...
[time] UTC NTP synchronization requested
[firebase] Client initialized; waiting for authentication token
```

## Step 2 — Confirm the Firebase write

After initialization, expect a message similar to:

```text
[sensor] Sample sequence=1 error_mask=0x00000000 location=configured
[firebase] Published /sensor_readings/odor-node-.../<push-id> sequence=1
```

If the write fails, verify:

1. Wi-Fi internet access.
2. Firebase API key and database URL.
3. Email/Password Authentication is enabled.
4. Device email and password.
5. Realtime Database write permissions.
6. ESP32 UTC time has synchronized.

## Step 3 — Verify the real record in Firebase

Open Firebase Console and navigate to:

```text
Build → Realtime Database → Data
sensor_readings/{device_id}/{push_id}
```

Expected schema:

```json
{
  "device_id": "odor-node-a1b2c3d4e5f6",
  "timestamp": "2026-09-12T07:30:00Z",
  "latitude": 18.5204,
  "longitude": 73.8567,
  "bme_gas": 23000,
  "mq135": 740,
  "mq136": 410,
  "mq3": 250,
  "temperature": 27.4,
  "humidity": 58,
  "pressure": 1007.5,
  "is_simulated": false
}
```

Confirm:

- `is_simulated` is `false`.
- `device_id` matches the Firebase parent key.
- Timestamp is UTC ISO-8601.
- MQ values are between `0` and `4095`.
- Humidity is between `0` and `100`.
- GPS coordinates match the GPS fix or configured fallback.

## Step 4 — Run FastAPI and ML prediction

```bash
cd ai-powered-real-time-odor-detection-system/backend
```

Activate the backend virtual environment, then run:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Check health:

```bash
curl http://localhost:8000/health
```

Expected healthy response:

```json
{
  "status": "healthy",
  "api": "ok",
  "firebase": "ok",
  "ml_model": "ok",
  "version": "0.2.0"
}
```

Copy one real ESP32 payload from Firebase and submit it:

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "odor-node-a1b2c3d4e5f6",
    "timestamp": "2026-09-12T07:30:00Z",
    "latitude": 18.5204,
    "longitude": 73.8567,
    "bme_gas": 23000,
    "mq135": 740,
    "mq136": 410,
    "mq3": 250,
    "temperature": 27.4,
    "humidity": 58,
    "pressure": 1007.5,
    "is_simulated": false
  }'
```

The response must contain:

```text
odor_class
intensity
anomaly_status
confidence
prediction_risk
timestamp
device_id
reading_id
prediction_id
```

Actual model values must not be invented.

> The current `/predict` route stores the submitted reading. Submitting an ESP32 record already stored in Firebase creates another reading, so use this only for controlled verification until an automatic Firebase processor is enabled.

## Step 5 — Confirm prediction and alerts in Firebase

Check:

```text
predictions/{device_id}/{prediction_id}
```

Verify that the prediction contains the same device ID, timestamp and reading ID, plus:

```text
odor_class
intensity
anomaly_status
confidence
prediction_risk
```

If the result is anomalous or high/critical risk, also check:

```text
alerts/{device_id}/{alert_id}
```

No alert for a normal low-risk reading is expected behavior.

## Step 6 — Start the React dashboard

```bash
cd ai-powered-real-time-odor-detection-system/frontend
cp .env.example .env
```

Set at least:

```dotenv
VITE_API_BASE_URL=http://localhost:8000
VITE_POLL_INTERVAL_MS=5000
```

For direct Firebase realtime updates, also set:

```dotenv
VITE_FIREBASE_API_KEY=your-web-api-key
VITE_FIREBASE_AUTH_DOMAIN=your-project-id.firebaseapp.com
VITE_FIREBASE_DATABASE_URL=https://your-project-id-default-rtdb.firebaseio.com
VITE_FIREBASE_PROJECT_ID=your-project-id
VITE_FIREBASE_APP_ID=your-web-app-id
VITE_FIREBASE_USE_ANONYMOUS_AUTH=true
```

Then run:

```bash
npm install
npm run typecheck
npm run verify:components
API_BASE_URL=http://localhost:8000 npm run test:api
npm run build
npm run dev
```

Open:

```text
http://localhost:5173
```

## Step 7 — Verify every dashboard output

Select the physical ESP32 device and verify:

1. **Real-time sensor values**
   - MQ-135, MQ-136, MQ-3, BME gas, temperature, humidity and pressure update.
   - Values match Firebase for the same timestamp.

2. **Odor status and intensity**
   - Odor class and intensity match the latest Firebase prediction.
   - No placeholder value remains after a real result arrives.

3. **Confidence and anomaly status**
   - Confidence matches the model result and displays as a percentage.
   - Anomaly status matches `anomaly_status` in Firebase.

4. **Prediction risk and alerts**
   - Risk matches `prediction_risk`.
   - High-risk or anomalous readings appear under Recent Alerts.

5. **Historical graphs**
   - Charts contain real ESP32 readings.
   - Timestamps are ordered correctly.
   - Missing values are not silently plotted as zero.

6. **Device status**
   - The correct ESP32 device ID appears.
   - Current readings show online status; delayed readings become stale/offline.

7. **GPS and map**
   - The map point matches Firebase latitude and longitude.
   - Coordinates match the GPS fix or configured fallback.

Open browser developer tools and confirm:

- No red console errors.
- `/health`, `/sensor-data`, `/devices`, `/latest` and `/alerts` return HTTP 200.
- Firebase listeners connect when enabled.
- No CORS errors occur.
- No secrets appear in browser logs or network payloads.

## Final pass criteria

The physical pipeline passes only when:

- ESP32 serial output reports successful Firebase writes.
- Firebase contains `is_simulated=false` readings.
- FastAPI health reports Firebase and ML as ready.
- ML prediction completes without an exception.
- Firebase stores the prediction and any required alert.
- The dashboard shows matching device, timestamp, sensor values, prediction, risk and location.
- Browser and backend logs contain no runtime errors.

A software-only test does not prove real-sensor accuracy. Calibrate sensors against known reference conditions before using predictions for safety decisions.
