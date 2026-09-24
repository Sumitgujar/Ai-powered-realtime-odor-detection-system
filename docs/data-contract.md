# Versioned sensor data contract

The Firebase architecture and `sensor_readings` root are preserved. Historical schema-v1 ESP32 records must remain unchanged.

## Schema v1 — legacy

Legacy records may contain:

```text
schemaVersion absent or 1
device_id
timestamp
mq135
mq136
mq3
bme_gas
temperature
humidity
pressure
latitude
longitude
is_simulated
```

These records are classified as legacy. Their old ML model and feature ordering are retained as a backup and must not be evaluated as schema-v2 performance.

## Schema v2 — NodeMCU configuration

New records use the same Firebase `sensor_readings/{deviceId}/{pushId}` architecture:

```json
{
  "deviceId": "nodemcu-1234abcd",
  "timestamp": "2026-09-18T17:45:00Z",
  "mq135": 740.0,
  "temperature": 27.4,
  "humidity": 58.0,
  "pressure": 1007.5,
  "pir": true,
  "schemaVersion": 2
}
```

When the physical BME680/BME68x exposes a usable gas channel, the record may additionally contain:

```json
{
  "bme_gas": 23000.0
}
```

The schema-v2 writer and validator do not add `mq136`, `mq3`, latitude, longitude, or a fake BME gas value.

## Compatibility rules

- Schema v1 and schema v2 coexist under the same Firebase root.
- Existing records are not deleted or rewritten.
- Firebase rules accept both versions and distinguish them using `schemaVersion`.
- Schema-v2 records require `deviceId`, `mq135`, environmental values, `pir`, and `schemaVersion: 2`.
- `bme_gas` is optional in schema v2.
- The existing FastAPI and React layers are intentionally unchanged in this migration and require a later explicit schema-v2 integration.
