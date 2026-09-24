# ESP8266 odor sensor firmware

PlatformIO firmware for the migrated NodeMCU sensor node.

## Hardware

- ESP8266 NodeMCU (`nodemcuv2`)
- MQ135 analog output on A0
- BME680/BME68x over I2C: SDA D2/GPIO4, SCL D1/GPIO5
- PIR output on D5/GPIO14

The active firmware has no MQ136, MQ3, or GPS hardware/library dependency.

## Configure and build

```bash
cd firmware
cp include/config.example.h include/config.h
# Fill Wi-Fi and Firebase values in include/config.h
pio run -e nodemcuv2
pio run -e nodemcuv2 -t upload
pio device monitor -b 115200
```

`include/config.h` is ignored by Git. Do not commit credentials.

## Firebase schema-v2 payload

The node writes to `/sensor_readings/<deviceId>/<push-id>`:

```json
{
  "deviceId": "odor-node-1234abcd",
  "timestamp": "2026-09-24T18:00:00Z",
  "mq135": 512.0,
  "temperature": 27.4,
  "humidity": 58.0,
  "pressure": 1007.5,
  "bme_gas": 23000.0,
  "pir": false,
  "schemaVersion": 2
}
```

`bme_gas` is emitted because this firmware uses an actual BME680/BME68x gas-resistance reading. Other schema-v2 writers may omit it when their hardware does not support that measurement.

See `WIRING.md` for voltage, warm-up, and calibration checks.
