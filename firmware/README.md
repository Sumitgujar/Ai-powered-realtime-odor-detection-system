# ESP8266 NodeMCU sensor node

This firmware is the controlled hardware migration from the previous ESP32 node:

- ESP32 → ESP8266 NodeMCU (`nodemcuv2`)
- MQ135 + MQ136 + MQ3 → MQ135 only
- BME688 → BME680/BME68x-compatible I2C sensor
- GPS → removed; static configured coordinates are used only for the unchanged backend contract
- PIR → added on D5/GPIO14

Firebase, ML, FastAPI, React, and the simulator were intentionally not modified.

## Hardware inputs

| Measurement | Hardware | Firmware input |
| --- | --- | --- |
| Gas | MQ135 analog output | NodeMCU A0 |
| Temperature, humidity, pressure, gas resistance | BME680/BME68x I2C breakout | SDA D2/GPIO4, SCL D1/GPIO5 |
| Motion | PIR digital output | D5/GPIO14 |

The Adafruit BME680 library is used for the basic BME68x temperature, humidity, pressure, and gas-resistance readings. The firmware does not use BME688 gas-scanner/AI features. Confirm the exact marking on the breakout before wiring it.

## Setup

1. Install PlatformIO Core or the PlatformIO VS Code extension.
2. Open this `firmware/` directory as the PlatformIO project.
3. Copy `include/config.example.h` to `include/config.h`.
4. Set Wi-Fi, Firebase Auth, database URL, static fallback coordinates, and calibration values.
5. Wire the hardware according to `WIRING.md`.
6. Enable Firebase Email/Password authentication and create a dedicated device account.

Never commit `include/config.h`.

## Commands

```bash
cd firmware
cp include/config.example.h include/config.h
pio pkg install
pio test -e native
pio run -e nodemcuv2
pio run -e nodemcuv2 --target upload
pio device monitor --baud 115200
```

## ESP8266 ADC warning

The ESP8266 chip ADC/TOUT input is specified by Espressif as 0–1.0 V. Many NodeMCU development boards add an onboard divider and expose A0 as a higher-range input, but the range is board-revision-dependent. Do not assume that every NodeMCU A0 accepts 3.3 V.

Before connecting MQ135 AO:

1. Identify the exact NodeMCU board and inspect its schematic.
2. Measure the MQ135 module AO voltage with a multimeter at the highest expected gas level.
3. Add an external divider or level-conditioning circuit if the MQ135 output can exceed the verified A0 limit.
4. Configure calibration only after the electrical range is safe.

The firmware reads the ESP8266 ADC count as 0–1023 and applies `MQ135_SCALE` and `MQ135_OFFSET`. It does not claim that the count is ppm.

## Firebase payload

The new hardware values are:

```json
{
  "device_id": "odor-node-1234abcd",
  "timestamp": "2026-09-18T17:45:00Z",
  "bme_gas": 23000.0,
  "mq135": 740.0,
  "temperature": 27.4,
  "humidity": 58.0,
  "pressure": 1007.5,
  "pir_motion": true,
  "is_simulated": false,
  "latitude": 18.5204,
  "longitude": 73.8567,
  "mq136": 0.0,
  "mq3": 0.0
}
```

`latitude`, `longitude`, `mq136`, and `mq3` are compatibility fields because the existing Firebase rules, FastAPI models, and ML feature pipeline were explicitly kept unchanged. They are not readings from GPS, MQ136, or MQ3 hardware. A later backend/schema migration is required before those fields can be removed safely.

## Reliability behavior

- Wi-Fi reconnect attempts occur at a bounded interval.
- Firebase token refresh/reconnect is handled by the Firebase client.
- Failed writes retain the latest sample for retry.
- Samples are collected every 10 seconds by default.
- Invalid NTP time or failed BME680/BME68x readings are not published.
- BME initialization is retried after failures.
- MQ135 ADC saturation and sensor errors are reported in the serial diagnostic mask.
- `is_simulated` is always `false` for this firmware.
- The device ID uses `DEVICE_ID_OVERRIDE` when set; otherwise it is derived from the ESP8266 chip ID.

## Serial verification

Expected messages:

```text
[boot] AI odor sensor node starting
[boot] Device ID: odor-node-...
[sensor] BME680/BME68x initialized
[wifi] Connecting to ...
[time] UTC NTP synchronization requested
[firebase] Client initialized; waiting for authentication token
[sensor] Sample sequence=1 error_mask=0x00000000 pir=clear
[firebase] Published /sensor_readings/odor-node-.../<push-id> sequence=1
```

The existing Python simulator remains available under `backend/simulator.py` and continues writing `is_simulated=true` records. It was not changed by this migration.
