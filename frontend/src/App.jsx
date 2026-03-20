/**
 * IoT Monitor - Dashboard
 *
 * TODO: Реализовать дашборд мониторинга IoT-датчиков
 *
 * Требования:
 * - Таблица событий: время, sensor_id, location, temperature, humidity, severity, notification_sent
 * - Цвета строк: normal (зелёный), warning (жёлтый), critical (красный)
 * - Фильтры: по severity, по sensor_id, по диапазону дат
 * - Карточки сверху: всего событий, critical за сегодня, последнее событие
 * - Автообновление данных каждые 3 секунды (polling GET /api/events)
 * - Кнопка "Симулировать датчик" - форма для отправки тестового webhook POST /webhooks/sensor
 *
 * Можно использовать: Tailwind, MUI, или чистый CSS - на твой выбор
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';

const SEVERITY_COLORS = {
  normal: '#16a34a', // green
  warning: '#f59e0b', // amber
  critical: '#dc2626', // red
};

function formatDateTime(value) {
  if (!value) return '-';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return String(value);
  return d.toLocaleString();
}

function toUtcDateKey(d) {
  // yyyy-mm-dd in UTC
  const y = d.getUTCFullYear();
  const m = String(d.getUTCMonth() + 1).padStart(2, '0');
  const day = String(d.getUTCDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function App() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [filterSeverity, setFilterSeverity] = useState('');
  const [filterSensorId, setFilterSensorId] = useState('');

  const [form, setForm] = useState({
    sensor_id: 'sensor-01',
    location: 'Склад А',
    temperature: 52.3,
    humidity: 45.0,
  });
  const [submitStatus, setSubmitStatus] = useState(null);

  const pollIntervalMs = 3000;
  const abortRef = useRef(null);

  const todayUtcKey = useMemo(() => toUtcDateKey(new Date()), []);

  const fetchEvents = useCallback(async () => {
    if (abortRef.current) abortRef.current.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      params.set('limit', '50');
      params.set('offset', '0');
      if (filterSeverity) params.set('severity', filterSeverity);
      if (filterSensorId.trim()) params.set('sensor_id', filterSensorId.trim());

      const resp = await fetch(`/api/events?${params.toString()}`, { signal: controller.signal });
      if (!resp.ok) {
        throw new Error(`GET /api/events failed: ${resp.status}`);
      }
      const data = await resp.json();
      setEvents(Array.isArray(data) ? data : []);
    } catch (e) {
      if (e?.name === 'AbortError') return;
      setError(e?.message || String(e));
    } finally {
      setLoading(false);
    }
  }, [filterSeverity, filterSensorId]);

  useEffect(() => {
    // Подкачиваем при старте и при изменении фильтров.
    fetchEvents();
  }, [fetchEvents]);

  useEffect(() => {
    const id = setInterval(() => {
      fetchEvents();
    }, pollIntervalMs);
    return () => clearInterval(id);
  }, [fetchEvents]);

  const stats = useMemo(() => {
    const total = events.length;
    const criticalToday = events.filter((e) => {
      if (e.severity !== 'critical') return false;
      const d = new Date(e.created_at);
      if (Number.isNaN(d.getTime())) return false;
      return toUtcDateKey(d) === todayUtcKey;
    }).length;
    const last = events[0] || null;
    return { total, criticalToday, last };
  }, [events, todayUtcKey]);

  const onSubmitSimulate = async (e) => {
    e.preventDefault();
    setSubmitStatus('Отправляю...');
    try {
      const payload = {
        sensor_id: String(form.sensor_id || '').trim(),
        location: String(form.location || '').trim(),
        temperature: Number(form.temperature),
        humidity: Number(form.humidity),
        timestamp: new Date().toISOString(), // FastAPI принимает ISO 8601
      };

      const resp = await fetch('/webhooks/sensor', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!resp.ok) {
        throw new Error(`POST /webhooks/sensor failed: ${resp.status}`);
      }
      const data = await resp.json();
      setSubmitStatus(`Принято: ${data.task_id || ''}`.trim());

      // Сразу обновим таблицу (автообновление всё равно есть).
      fetchEvents();
    } catch (err) {
      setSubmitStatus(err?.message || String(err));
    }
  };

  return (
    <div className="app">
      <style>{`
        .app { font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; background: #0b1220; color: #e5e7eb; min-height: 100vh; padding: 24px; }
        .wrap { max-width: 1200px; margin: 0 auto; }
        .header { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; margin-bottom: 18px; }
        .title { font-size: 24px; font-weight: 700; margin: 0; }
        .subtitle { opacity: 0.8; margin: 6px 0 0; font-size: 13px; }
        .cards { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; margin-bottom: 16px; }
        .card { background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12); border-radius: 14px; padding: 14px; }
        .card .k { opacity: 0.75; font-size: 13px; margin-bottom: 8px; }
        .card .v { font-size: 22px; font-weight: 800; line-height: 1.1; }
        .card .hint { opacity: 0.75; font-size: 12px; margin-top: 6px; }
        .grid { display: grid; grid-template-columns: 1fr 360px; gap: 14px; align-items: start; }
        .panel { background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12); border-radius: 14px; padding: 14px; }
        .panel h2 { margin: 0 0 12px; font-size: 14px; opacity: 0.9; text-transform: uppercase; letter-spacing: .08em; }
        .filters { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 12px; }
        .field { display: flex; flex-direction: column; gap: 6px; }
        label { font-size: 12px; opacity: 0.8; }
        input, select { padding: 10px 12px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.16); background: rgba(0,0,0,0.2); color: #e5e7eb; outline: none; }
        input::placeholder { color: rgba(229,231,235,0.55); }
        .btn { padding: 10px 12px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.16); background: rgba(255,255,255,0.08); color: #e5e7eb; cursor: pointer; font-weight: 600; }
        .btn:hover { background: rgba(255,255,255,0.12); }
        .table { width: 100%; border-collapse: collapse; }
        .table th, .table td { padding: 10px 8px; border-bottom: 1px solid rgba(255,255,255,0.08); font-size: 13px; }
        .table th { text-align: left; opacity: 0.85; font-weight: 700; }
        .sev { font-weight: 800; }
        .badge { display: inline-block; padding: 4px 8px; border-radius: 999px; font-size: 12px; font-weight: 800; }
        .loading { opacity: 0.75; font-size: 13px; padding: 10px 0; }
        .err { color: #fca5a5; font-size: 13px; padding: 10px 0; white-space: pre-wrap; }
        .formGrid { display: grid; grid-template-columns: 1fr; gap: 10px; }
        .muted { opacity: 0.75; font-size: 12px; line-height: 1.3; }
        .last { display: flex; flex-direction: column; gap: 8px; }
        .lastRow { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; }
      `}</style>

      <div className="wrap">
        <div className="header">
          <div>
            <h1 className="title">IoT Monitor</h1>
            <p className="subtitle">Дашборд событий датчиков (обновление каждые 3 секунды)</p>
          </div>
          <div className="muted">{loading ? 'Загрузка...' : error ? 'Ошибка загрузки' : 'Готово'}</div>
        </div>

        <div className="cards">
          <div className="card">
            <div className="k">Всего событий</div>
            <div className="v">{stats.total}</div>
            <div className="hint">по текущей выборке</div>
          </div>
          <div className="card">
            <div className="k">Critical за сегодня (UTC)</div>
            <div className="v" style={{ color: SEVERITY_COLORS.critical }}>{stats.criticalToday}</div>
            <div className="hint">из текущей выборки</div>
          </div>
          <div className="card">
            <div className="k">Последнее событие</div>
            {stats.last ? (
              <div className="last">
                <div className="lastRow">
                  <div style={{ fontWeight: 800 }}>{stats.last.sensor_id}</div>
                  <span
                    className="badge"
                    style={{ background: `${SEVERITY_COLORS[stats.last.severity] || '#64748b'}22`, color: SEVERITY_COLORS[stats.last.severity] || '#64748b' }}
                  >
                    {stats.last.severity}
                  </span>
                </div>
                <div className="muted">{formatDateTime(stats.last.created_at)} • {stats.last.location}</div>
              </div>
            ) : (
              <div className="muted">Пока нет данных</div>
            )}
          </div>
        </div>

        <div className="grid">
          <div className="panel">
            <h2>События</h2>

            <div className="filters">
              <div className="field">
                <label>Severity</label>
                <select value={filterSeverity} onChange={(e) => setFilterSeverity(e.target.value)}>
                  <option value="">Все</option>
                  <option value="normal">normal</option>
                  <option value="warning">warning</option>
                  <option value="critical">critical</option>
                </select>
              </div>

              <div className="field">
                <label>Sensor ID</label>
                <input
                  value={filterSensorId}
                  onChange={(e) => setFilterSensorId(e.target.value)}
                  placeholder="например: sensor-01"
                />
              </div>

              <div className="field" style={{ justifyContent: 'flex-end' }}>
                <button className="btn" type="button" onClick={fetchEvents}>
                  Обновить
                </button>
              </div>
            </div>

            {loading && <div className="loading">Загружаю события...</div>}
            {error && <div className="err">{error}</div>}

            <div style={{ overflowX: 'auto' }}>
              <table className="table">
                <thead>
                  <tr>
                    <th>Время</th>
                    <th>sensor_id</th>
                    <th>location</th>
                    <th>Темп. °C</th>
                    <th>Влажн. %</th>
                    <th>severity</th>
                    <th>Уведомление</th>
                  </tr>
                </thead>
                <tbody>
                  {!events.length ? (
                    <tr>
                      <td colSpan="7" className="muted">Нет событий по выбранным фильтрам</td>
                    </tr>
                  ) : (
                    events.map((e) => (
                      <tr key={e.id ?? `${e.sensor_id}-${e.created_at}`}>
                        <td>{formatDateTime(e.created_at)}</td>
                        <td style={{ fontWeight: 700 }}>{e.sensor_id}</td>
                        <td>{e.location}</td>
                        <td>{typeof e.temperature === 'number' ? e.temperature.toFixed(1) : e.temperature}</td>
                        <td>{typeof e.humidity === 'number' ? e.humidity.toFixed(1) : e.humidity}</td>
                        <td>
                          <span className="badge" style={{ background: `${SEVERITY_COLORS[e.severity] || '#64748b'}22`, color: SEVERITY_COLORS[e.severity] || '#64748b' }}>
                            <span className="sev">{e.severity}</span>
                          </span>
                        </td>
                        <td>{e.notification_sent ? 'Да' : '-'}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <div className="panel">
            <h2>Симулировать датчик</h2>

            <form className="formGrid" onSubmit={onSubmitSimulate}>
              <div className="field">
                <label>sensor_id</label>
                <input
                  value={form.sensor_id}
                  onChange={(e) => setForm((s) => ({ ...s, sensor_id: e.target.value }))}
                />
              </div>

              <div className="field">
                <label>location</label>
                <input
                  value={form.location}
                  onChange={(e) => setForm((s) => ({ ...s, location: e.target.value }))}
                />
              </div>

              <div className="field">
                <label>temperature (°C)</label>
                <input
                  type="number"
                  step="0.1"
                  value={form.temperature}
                  onChange={(e) => setForm((s) => ({ ...s, temperature: e.target.value }))}
                />
              </div>

              <div className="field">
                <label>humidity (%)</label>
                <input
                  type="number"
                  step="0.1"
                  value={form.humidity}
                  onChange={(e) => setForm((s) => ({ ...s, humidity: e.target.value }))}
                />
              </div>

              <button className="btn" type="submit">
                Отправить webhook
              </button>

              {submitStatus && <div className="muted">{submitStatus}</div>}

              <div className="muted">
                Отправляет POST на <code>/webhooks/sensor</code>. Дальше задача уходит в Celery, а уведомление приходит только при <b>critical</b>.
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
