import { parseAlertList, parseSensorList } from './parsers';
import type { HealthStatus, PredictionAlert, SensorRecord } from '../types/monitoring';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');

async function json(path: string): Promise<unknown> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { Accept: 'application/json' },
  });
  if (!response.ok) {
    const body = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${body}`);
  }
  return response.json();
}

export async function fetchLatest(deviceId?: string): Promise<SensorRecord[]> {
  const query = deviceId ? `?device_id=${encodeURIComponent(deviceId)}` : '';
  return parseSensorList(await json(`/latest${query}`));
}

export async function fetchSensorHistory(deviceId?: string): Promise<SensorRecord[]> {
  const params = new URLSearchParams({ limit: '100' });
  if (deviceId) params.set('device_id', deviceId);
  return parseSensorList(await json(`/sensor-data?${params.toString()}`));
}

export async function fetchAlerts(deviceId?: string): Promise<PredictionAlert[]> {
  const params = new URLSearchParams({ limit: '50' });
  if (deviceId) params.set('device_id', deviceId);
  return parseAlertList(await json(`/alerts?${params.toString()}`));
}

export async function fetchHealth(): Promise<HealthStatus> {
  return (await json('/health')) as HealthStatus;
}
