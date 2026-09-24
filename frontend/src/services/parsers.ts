import type { PredictionAlert, SensorRecord } from '../types/monitoring';

type JsonObject = Record<string, unknown>;

const object = (value: unknown): JsonObject => {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error('Expected an object');
  }
  return value as JsonObject;
};

const text = (value: unknown, field: string): string => {
  if (typeof value !== 'string' || value.trim() === '') throw new Error(`Invalid ${field}`);
  return value;
};

const number = (value: unknown, field: string): number => {
  if (typeof value !== 'number' || !Number.isFinite(value)) throw new Error(`Invalid ${field}`);
  return value;
};

export function parseSensorRecord(value: unknown, fallbackId = ''): SensorRecord {
  const row = object(value);
  const version = row.schemaVersion === 2 ? 2 : 1;
  const deviceId = text(version === 2 ? row.deviceId : row.device_id, 'device ID');
  const readingId = typeof row.reading_id === 'string' ? row.reading_id : fallbackId;
  const result: SensorRecord = {
    readingId,
    deviceId,
    timestamp: text(row.timestamp, 'timestamp'),
    schemaVersion: version,
    mq135: number(row.mq135, 'mq135'),
    temperature: number(row.temperature, 'temperature'),
    humidity: number(row.humidity, 'humidity'),
    pressure: number(row.pressure, 'pressure'),
    isLegacy: version === 1,
  };
  if (typeof row.bme_gas === 'number' && Number.isFinite(row.bme_gas)) result.bmeGas = row.bme_gas;
  if (version === 2) {
    if (typeof row.pir !== 'boolean') throw new Error('Invalid pir');
    result.pir = row.pir;
  }
  return result;
}

export function parseSensorList(value: unknown): SensorRecord[] {
  if (!Array.isArray(value)) throw new Error('Expected a sensor array');
  return value.map((row) => parseSensorRecord(row));
}

export function parseFirebaseSensorSnapshot(value: unknown): SensorRecord[] {
  const root = object(value);
  const records: SensorRecord[] = [];
  for (const [deviceId, readingsValue] of Object.entries(root)) {
    const readings = object(readingsValue);
    for (const [readingKey, row] of Object.entries(readings)) {
      const parsed = parseSensorRecord(row, `${deviceId}/${readingKey}`);
      if (parsed.deviceId !== deviceId) throw new Error('Firebase device key mismatch');
      records.push(parsed);
    }
  }
  return records.sort((a, b) => Date.parse(b.timestamp) - Date.parse(a.timestamp));
}

export function parseAlert(value: unknown): PredictionAlert {
  const row = object(value);
  const version = row.schemaVersion === 2 ? 2 : 1;
  return {
    alertId: text(row.alert_id, 'alert_id'),
    deviceId: text(version === 2 ? row.deviceId : row.device_id, 'device ID'),
    timestamp: text(row.timestamp, 'timestamp'),
    odorClass: text(row.odor_class, 'odor_class'),
    intensity: text(row.intensity, 'intensity'),
    anomalyStatus: Boolean(row.anomaly_status),
    confidence: number(row.confidence, 'confidence'),
    predictionRisk: text(row.prediction_risk, 'prediction_risk'),
    schemaVersion: version,
  };
}

export function parseAlertList(value: unknown): PredictionAlert[] {
  if (!Array.isArray(value)) throw new Error('Expected an alert array');
  return value.map(parseAlert);
}
