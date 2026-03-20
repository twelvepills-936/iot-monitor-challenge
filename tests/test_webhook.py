from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from sqlalchemy import select, text

from app.db import get_session
from app.models.event import SensorEvent
from app.tasks.process import _classify_severity, process_sensor_event


def _parse_timestamp(ts: str):
    # Тесты задают timestamp в формате ISO с Z; в задаче используется аналогичная логика.
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    from datetime import datetime

    dt = datetime.fromisoformat(ts)
    return dt


def test_webhook_valid_data(client, monkeypatch):
    # endpoint импортирует process_sensor_event из app.tasks.process.
    # Мокаем apply_async, чтобы не требовать брокер/БД.
    from app.api import webhooks as webhooks_module

    class DummyAsyncResult:
        def __init__(self, id_):
            self.id = id_

    monkeypatch.setattr(
        webhooks_module.process_sensor_event,
        "apply_async",
        lambda *args, **kwargs: DummyAsyncResult("test-task-id-123"),
    )

    payload = {
        "sensor_id": "sensor-01",
        "location": "Склад А",
        "temperature": 52.3,
        "humidity": 45.0,
        "timestamp": "2026-03-04T10:30:00Z",
    }

    resp = client.post("/webhooks/sensor", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "accepted"
    assert data["task_id"] == "test-task-id-123"


def test_webhook_invalid_data(client):
    payload = {
        "sensor_id": "sensor-01",
        "location": "Склад А",
        "temperature": 52.3,
        # "humidity" missing
        "timestamp": "2026-03-04T10:30:00Z",
    }

    resp = client.post("/webhooks/sensor", json=payload)
    assert resp.status_code == 422


def _db_available():
    async def _check():
        try:
            async with get_session() as session:
                await session.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

    return asyncio.run(_check())


def test_process_event_success():
    if not _db_available():
        pytest.skip("PostgreSQL is not available for task DB test")

    sensor_id = "sensor-01"
    location = "Склад А"
    temperature = 30.0
    humidity = 40.0
    timestamp = "2026-03-04T10:30:00Z"
    created_at = _parse_timestamp(timestamp)

    class DummySelf:
        request = SimpleNamespace(retries=0)
        max_retries = 3

        def retry(self, **kwargs):
            raise AssertionError("retry() should not be called for normal events")

    dummy_self = DummySelf()
    result = process_sensor_event.run(
        dummy_self,
        sensor_id=sensor_id,
        location=location,
        temperature=temperature,
        humidity=humidity,
        timestamp=timestamp,
    )
    assert result["severity"] == "normal"
    assert result["notification_sent"] is False

    async def _fetch():
        async with get_session() as session:
            stmt = (
                select(SensorEvent)
                .where(SensorEvent.sensor_id == sensor_id, SensorEvent.created_at == created_at)
                .limit(1)
            )
            res = await session.execute(stmt)
            return res.scalars().first()

    event = asyncio.run(_fetch())
    assert event is not None
    assert event.severity == "normal"
    assert event.notification_sent is False
    assert event.error_message is None


def test_process_event_telegram_retry(monkeypatch):
    if not _db_available():
        pytest.skip("PostgreSQL is not available for task retry DB test")

    sensor_id = "sensor-01"
    location = "Склад А"
    temperature = 52.3
    humidity = 45.0
    timestamp = "2026-03-04T10:30:00Z"
    created_at = _parse_timestamp(timestamp)

    from app.tasks import process as process_module

    class DummyRetryException(Exception):
        pass

    def _raise_telegram(*args, **kwargs):
        raise RuntimeError("telegram is down")

    monkeypatch.setattr(process_module, "_send_telegram_critical", _raise_telegram)

    class DummySelf:
        request = SimpleNamespace(retries=0)
        max_retries = 3
        countdown = None

        def retry(self, exc=None, countdown=None, **kwargs):
            self.countdown = countdown
            raise DummyRetryException()

    dummy_self = DummySelf()

    with pytest.raises(DummyRetryException):
        process_sensor_event.run(
            dummy_self,
            sensor_id=sensor_id,
            location=location,
            temperature=temperature,
            humidity=humidity,
            timestamp=timestamp,
        )

    assert dummy_self.countdown == 1  # 2 ** 0

    async def _fetch():
        async with get_session() as session:
            stmt = (
                select(SensorEvent)
                .where(SensorEvent.sensor_id == sensor_id, SensorEvent.created_at == created_at)
                .limit(1)
            )
            res = await session.execute(stmt)
            return res.scalars().first()

    event = asyncio.run(_fetch())
    assert event is not None
    assert event.severity == "critical"
    assert event.notification_sent is False
    assert event.error_message is not None and "telegram is down" in event.error_message


def test_severity_classification():
    # По rules.json: temp warning > 35, temp critical > 50; humidity warning > 80, critical > 95
    sensor_id = "sensor-01"
    location = "Склад А"

    assert _classify_severity(sensor_id, location, temperature=50.0, humidity=40.0) == "warning"
    assert _classify_severity(sensor_id, location, temperature=50.1, humidity=40.0) == "critical"

    assert _classify_severity(sensor_id, location, temperature=35.0, humidity=40.0) == "normal"
    assert _classify_severity(sensor_id, location, temperature=35.1, humidity=40.0) == "warning"

    assert _classify_severity(sensor_id, location, temperature=30.0, humidity=80.0) == "normal"
    assert _classify_severity(sensor_id, location, temperature=30.0, humidity=80.1) == "warning"

    assert _classify_severity(sensor_id, location, temperature=30.0, humidity=95.0) == "warning"
    assert _classify_severity(sensor_id, location, temperature=30.0, humidity=95.1) == "critical"
