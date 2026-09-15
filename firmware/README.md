# ESP32 real sensor node

This PlatformIO firmware reads three analog MQ gas channels, a BME688 environmental sensor, and an optional UART GPS. It assigns a stable ESP32 device ID, obtains UTC time through NTP, authenticates with Firebase, and pushes validated JSON to:

```text
/sensor_readings/{device_id}/{firebase_push_id}
```

The existing Python simulator remains unchanged under `backend/simulator.py` and continues writing records with `is_simulated=true`. ESP32 records always use `is_simulated=false`.

## Setup

1. Install VS Code and the PlatformIO extension, or PlatformIO Core.
2. Open the `firmware/` directory as the PlatformIO project.
3. Copy `include/config.example.h` to `include/config.h`.
4. Fill Wi-Fi, Firebase Auth, database URL, location, pins, and calibration values.
5. Enable Email/Password authentication in Firebase and create a dedicated device account.
6. Wire hardware according to `WIRING.md`.

Never commit `include/config.h`.

## Commands

```bash
cd firmware
cp include/config.example.h include/config.h
pio pkg install
pio run
pio run --target upload
pio device monitor --baud 115200
```

Run host calibration tests:

```bash
pio test -e native
```

## JSON payload

```json
{
  "device_id": "odor-node-a1b2c3d4e5f6",
  "timestamp": "2026-09-12T07:30:00Z",
  "latitude": 18.5204,
  "longitude": 73.8567,
  "bme_gas": 23000.0,
  "mq135": 740.0,
  "mq136": 410.0,
  "mq3": 250.0,
  "temperature": 27.4,
  "humidity": 58.0,
  "pressure": 1007.5,
  "is_simulated": false
}
```

## Reliability behavior

- Wi-Fi reconnect attempts occur at a bounded interval.
- Firebase token refresh/reconnect is handled by the Firebase client; failed writes retain the latest pending sample for retry.
- Samples are collected every 10 seconds by default.
- Invalid NTP time or failed BME688 readings are not published.
- Missing GPS fixes use configured fallback coordinates and set an error bit in the serial diagnostic log.
- Saturated MQ channels are reported through the serial diagnostic error mask.
- BME688 initialization is retried after failures.
- Firebase payload keys remain exactly compatible with FastAPI `POST /predict` validation.

## End-to-end verification

1. Start FastAPI and confirm `/health` reports Firebase and ML as ready.
2. Flash the ESP32 and watch the serial monitor for a Firebase push ID.
3. Confirm the same reading exists in Firebase under the device ID.
4. Process the reading through FastAPI `/predict` or the configured Firebase ingestion processor.
5. Confirm a prediction is written under `/predictions/{device_id}`.
6. Open the React dashboard and select the ESP32 device.
7. Confirm live values, prediction, risk, GPS point, device status, and any alerts.

A physical real-sensor test requires the actual ESP32, sensors, Firebase credentials, trained model, and running backend/dashboard; it cannot be completed in a software-only sandbox.
