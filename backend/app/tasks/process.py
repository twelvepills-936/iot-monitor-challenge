"""
Celery-задача обработки событий от датчиков.

Задача:
- загрузка правил из rules.json
- классификация severity
- при critical: отправка в Telegram (mock API) с retry
- сохранение события в PostgreSQL
"""

from __future__ import annotations

import threading
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx
from sqlalchemy import select

from app.config import settings
from app.db import get_session, init_db
from app.models.event import SensorEvent
from app.tasks import celery_app


_RULES_CACHE: dict | None = None

# Async SQLAlchemy/asyncpg привязываются к event loop.
# Celery task синхронная, поэтому поднимаем один event loop в фоне и выполняем
# все coroutine в нём, чтобы не ловить "attached to a different loop".
_ASYNC_LOOP: object | None = None
_ASYNC_LOOP_THREAD: threading.Thread | None = None
_ASYNC_LOOP_LOCK = threading.Lock()


def _load_rules() -> dict:
    global _RULES_CACHE
    if _RULES_CACHE is not None:
        return _RULES_CACHE

    candidates = [
        Path("rules.json"),
        Path(__file__).resolve().parents[3] / "rules.json",
    ]
    rules_path = next((p for p in candidates if p.exists()), None)
    if rules_path is None:
        raise FileNotFoundError("rules.json not found")

    _RULES_CACHE = json.loads(rules_path.read_text(encoding="utf-8"))
    return _RULES_CACHE


def _parse_timestamp(ts: str) -> datetime:
    ts = ts.strip()
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _classify_severity(
    sensor_id: str,
    location: str,
    temperature: float,
    humidity: float,
) -> str:
    rules = _load_rules()

    temp_critical = float(rules["temperature"]["thresholds"]["critical"])
    temp_warning = float(rules["temperature"]["thresholds"]["warning"])
    humidity_critical = float(rules["humidity"]["thresholds"]["critical"])
    humidity_warning = float(rules["humidity"]["thresholds"]["warning"])

    if temperature > temp_critical or humidity > humidity_critical:
        return "critical"
    if temperature > temp_warning or humidity > humidity_warning:
        return "warning"
    return "normal"


def _build_telegram_text(sensor_id: str, location: str, temperature: float) -> str:
    temperature_str = f"{temperature:g}"
    return f"🚨 CRITICAL: {sensor_id} ({location}) — {temperature_str}°C"


def _send_telegram_critical(sensor_id: str, location: str, temperature: float) -> None:
    url = f"{settings.telegram_api_url}/bot{settings.telegram_bot_token}/sendMessage"
    payload = {
        "chat_id": settings.telegram_chat_id,
        "text": _build_telegram_text(sensor_id, location, temperature),
    }
    resp = httpx.post(url, json=payload, timeout=10.0)
    if resp.status_code >= 400:
        raise RuntimeError(f"Telegram error: HTTP {resp.status_code}")


async def _upsert_event_async(
    *,
    sensor_id: str,
    location: str,
    temperature: float,
    humidity: float,
    severity: str,
    created_at: datetime,
    notification_sent: bool,
    error_message: str | None,
) -> SensorEvent:
    # init_db() гарантирует наличие таблицы.
    await init_db()

    async with get_session() as session:
        stmt = select(SensorEvent).where(
            SensorEvent.sensor_id == sensor_id,
            SensorEvent.created_at == created_at,
        )
        res = await session.execute(stmt)
        event = res.scalars().first()

        if event is None:
            event = SensorEvent(
                sensor_id=sensor_id,
                location=location,
                temperature=temperature,
                humidity=humidity,
                severity=severity,
                notification_sent=notification_sent,
                error_message=error_message,
                created_at=created_at,
            )
            session.add(event)
        else:
            event.location = location
            event.temperature = temperature
            event.humidity = humidity
            event.severity = severity

            # Не затираем успех: если уведомление уже отправлено, оставляем.
            if not event.notification_sent:
                event.notification_sent = notification_sent
                event.error_message = error_message

        await session.commit()
        await session.refresh(event)
        return event


def _run_async(coro):
    import asyncio

    global _ASYNC_LOOP, _ASYNC_LOOP_THREAD

    # Создаём loop один раз на процесс.
    if _ASYNC_LOOP is None or _ASYNC_LOOP_THREAD is None:
        with _ASYNC_LOOP_LOCK:
            if _ASYNC_LOOP is None or _ASYNC_LOOP_THREAD is None:
                loop = asyncio.new_event_loop()

                def _runner():
                    asyncio.set_event_loop(loop)
                    loop.run_forever()

                t = threading.Thread(target=_runner, daemon=True)
                t.start()
                _ASYNC_LOOP = loop
                _ASYNC_LOOP_THREAD = t

    fut = asyncio.run_coroutine_threadsafe(coro, _ASYNC_LOOP)  # type: ignore[arg-type]
    return fut.result()


@celery_app.task(name="process_sensor_event", bind=True, max_retries=3)
def process_sensor_event(
    self,
    sensor_id: str,
    location: str,
    temperature: float,
    humidity: float,
    timestamp: str,
):
    created_at = _parse_timestamp(timestamp)
    severity = _classify_severity(sensor_id, location, temperature, humidity)

    # Всегда сохраняем событие.
    _run_async(
        _upsert_event_async(
            sensor_id=sensor_id,
            location=location,
            temperature=temperature,
            humidity=humidity,
            severity=severity,
            created_at=created_at,
            notification_sent=False,
            error_message=None,
        )
    )

    if severity != "critical":
        return {
            "sensor_id": sensor_id,
            "location": location,
            "temperature": temperature,
            "humidity": humidity,
            "severity": severity,
            "notification_sent": False,
        }

    # Для critical: отправляем уведомление с retry.
    try:
        _send_telegram_critical(sensor_id=sensor_id, location=location, temperature=temperature)
    except Exception as exc:
        # Фиксируем ошибку до retry.
        _run_async(
            _upsert_event_async(
                sensor_id=sensor_id,
                location=location,
                temperature=temperature,
                humidity=humidity,
                severity=severity,
                created_at=created_at,
                notification_sent=False,
                error_message=str(exc),
            )
        )

        if self.request.retries < self.max_retries:
            countdown = 2 ** self.request.retries
            raise self.retry(exc=exc, countdown=countdown)

        raise

    # Telegram отправлен успешно.
    event = _run_async(
        _upsert_event_async(
            sensor_id=sensor_id,
            location=location,
            temperature=temperature,
            humidity=humidity,
            severity=severity,
            created_at=created_at,
            notification_sent=True,
            error_message=None,
        )
    )

    return {
        "sensor_id": sensor_id,
        "location": location,
        "temperature": temperature,
        "humidity": humidity,
        "severity": severity,
        "notification_sent": True,
        "event_id": event.id,
    }
