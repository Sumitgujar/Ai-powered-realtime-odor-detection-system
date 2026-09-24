import { type ChangeEvent, useEffect, useMemo, useState } from 'react';
import { fetchAlerts, fetchHealth, fetchLatest, fetchSensorHistory } from './services/api';
import type { HealthStatus, PredictionAlert, SensorRecord } from './types/monitoring';

const format = (value: number | undefined, unit = '') =>
  value === undefined ? 'Not supported' : `${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}${unit}`;

function App() {
  const [records, setRecords] = useState<SensorRecord[]>([]);
  const [alerts, setAlerts] = useState<PredictionAlert[]>([]);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [selectedDevice, setSelectedDevice] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const devices = useMemo(
    () => Array.from(new Set(records.map((record) => record.deviceId))).sort(),
    [records],
  );
  const visible = selectedDevice
    ? records.filter((record) => record.deviceId === selectedDevice)
    : records;
  const latest = visible[0];
  const latestAlert = alerts.find((alert) => !selectedDevice || alert.deviceId === selectedDevice);

  useEffect(() => {
    let active = true;
    const refresh = async () => {
      try {
        const [latestRows, historyRows, alertRows, healthValue] = await Promise.all([
          fetchLatest(selectedDevice || undefined),
          fetchSensorHistory(selectedDevice || undefined),
          fetchAlerts(selectedDevice || undefined),
          fetchHealth(),
        ]);
        if (!active) return;
        setRecords(historyRows.length ? historyRows : latestRows);
        setAlerts(alertRows);
        setHealth(healthValue);
        setError('');
      } catch (reason) {
        if (active) setError(reason instanceof Error ? reason.message : 'Unable to load monitoring data');
      } finally {
        if (active) setLoading(false);
      }
    };
    void refresh();
    const interval = window.setInterval(refresh, Number(import.meta.env.VITE_POLL_INTERVAL_MS || 5000));
    return () => {
      active = false;
      window.clearInterval(interval);
    };
  }, [selectedDevice]);

  return (
    <main className="app-shell">
      <header className="header">
        <div>
          <p className="eyebrow">Environmental monitoring</p>
          <h1>Odor Detection Dashboard</h1>
          <p>Schema-v2 NodeMCU readings with legacy record compatibility.</p>
        </div>
        <div className={`status ${health?.status === 'healthy' ? 'healthy' : 'degraded'}`}>
          {health ? `API ${health.status}` : 'Checking API'}
        </div>
      </header>

      <section className="toolbar">
        <label htmlFor="device">Device</label>
        <select id="device" value={selectedDevice} onChange={(event: ChangeEvent<HTMLSelectElement>) => setSelectedDevice(event.target.value)}>
          <option value="">All devices</option>
          {devices.map((device) => <option key={device} value={device}>{device}</option>)}
        </select>
        {latest && <span>Last reading: {new Date(latest.timestamp).toLocaleString()}</span>}
      </section>

      {loading && <section className="notice">Loading real sensor data…</section>}
      {error && <section className="notice error">{error}</section>}
      {!loading && !error && !latest && <section className="notice">No sensor readings are available.</section>}

      {latest && (
        <>
          <section className="metric-grid" aria-label="Latest sensor values">
            <article><span>MQ135</span><strong>{format(latest.mq135)}</strong></article>
            <article><span>Temperature</span><strong>{format(latest.temperature, ' °C')}</strong></article>
            <article><span>Humidity</span><strong>{format(latest.humidity, ' %')}</strong></article>
            <article><span>Pressure</span><strong>{format(latest.pressure, ' hPa')}</strong></article>
            <article><span>BME gas</span><strong>{format(latest.bmeGas, ' Ω')}</strong></article>
            <article><span>PIR presence</span><strong>{latest.pir === undefined ? 'Legacy record' : latest.pir ? 'Motion' : 'Clear'}</strong></article>
          </section>

          <section className="panel">
            <div>
              <h2>Current device</h2>
              <p>{latest.deviceId} · Schema v{latest.schemaVersion}</p>
            </div>
            <div>
              <h2>ML output</h2>
              {latestAlert ? (
                <p>{latestAlert.odorClass} · {latestAlert.intensity} · {(latestAlert.confidence * 100).toFixed(1)}% · {latestAlert.predictionRisk}</p>
              ) : (
                <p>No persisted alert output is available. Values are not fabricated.</p>
              )}
            </div>
          </section>

          <section className="panel history">
            <h2>Recent readings</h2>
            <div className="table-wrap">
              <table>
                <thead><tr><th>Time</th><th>Device</th><th>MQ135</th><th>Temp</th><th>Humidity</th><th>Pressure</th><th>BME gas</th><th>PIR</th></tr></thead>
                <tbody>
                  {visible.slice(0, 20).map((record) => (
                    <tr key={record.readingId || `${record.deviceId}-${record.timestamp}`}>
                      <td>{new Date(record.timestamp).toLocaleString()}</td><td>{record.deviceId}</td>
                      <td>{format(record.mq135)}</td><td>{format(record.temperature, ' °C')}</td>
                      <td>{format(record.humidity, ' %')}</td><td>{format(record.pressure, ' hPa')}</td>
                      <td>{format(record.bmeGas)}</td><td>{record.pir === undefined ? '—' : record.pir ? 'Motion' : 'Clear'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </main>
  );
}

export default App;
