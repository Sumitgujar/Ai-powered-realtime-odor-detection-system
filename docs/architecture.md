# System architecture

```text
ESP8266 NodeMCU
  ├─ MQ135 → A0
  ├─ BME680/BME68x → I2C D2/GPIO4 (SDA), D1/GPIO5 (SCL)
  └─ PIR → D5/GPIO14
        ↓ Wi-Fi
Firebase Realtime Database (schema v2; schema-v1 history preserved)
        ↓
FastAPI validation, reads, and explicit prediction endpoint
        ↓
Schema-matched Python ML artifact
        ↓
Firebase predictions/alerts
        ↓
React dashboard through FastAPI
```

The firmware writes sensor records directly to Firebase. FastAPI reads those records for dashboard endpoints. ML inference is currently initiated through `POST /predict`; the repository does not contain an automatic Firebase-triggered inference worker.
