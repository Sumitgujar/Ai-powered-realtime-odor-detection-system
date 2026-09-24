export type SchemaVersion = 1 | 2;

export interface SensorRecord {
  readingId: string;
  deviceId: string;
  timestamp: string;
  schemaVersion: SchemaVersion;
  mq135: number;
  temperature: number;
  humidity: number;
  pressure: number;
  bmeGas?: number;
  pir?: boolean;
  isLegacy: boolean;
}

export interface PredictionAlert {
  alertId: string;
  deviceId: string;
  timestamp: string;
  odorClass: string;
  intensity: string;
  anomalyStatus: boolean;
  confidence: number;
  predictionRisk: string;
  schemaVersion: SchemaVersion;
}

export interface HealthStatus {
  status: 'healthy' | 'degraded';
  api: 'ok';
  firebase: 'ok' | 'unavailable';
  ml_model: 'ok' | 'unavailable';
  version: string;
}
