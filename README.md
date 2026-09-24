# AI-Powered Real-Time Odor Detection System

Modular odor monitoring system using an ESP8266 NodeMCU, Firebase Realtime Database, FastAPI, a schema-versioned Python ML pipeline, and React.

## Current hardware

- MQ135 → A0
- BME680/BME68x → D2/GPIO4 SDA and D1/GPIO5 SCL
- PIR → D5/GPIO14

## Data flow

```text
ESP8266 sensors → Wi-Fi → Firebase RTDB → FastAPI → Python ML → Firebase predictions/alerts → React dashboard
```

Firmware records use schema version 2. Existing schema-v1 records and their legacy ML path remain readable for compatibility.

ML inference is performed by `POST /predict`; there is no automatic Firebase-triggered prediction worker in this repository.

See:

- `firmware/README.md` and `firmware/WIRING.md`
- `docs/data-contract.md`
- `backend/README.md`
- `ml/README.md`
- `frontend/.env.example`
