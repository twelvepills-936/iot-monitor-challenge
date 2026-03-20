"""
Webhook endpoint для приёма данных от IoT-датчиков.

Реализация:
- POST /webhooks/sensor
  - Принимает JSON с sensor_id, location, temperature, humidity, timestamp
  - Валидирует вход через Pydantic
  - Ставит задачу в Celery-очередь (без синхронной обработки)
  - Возвращает {"status": "accepted", "task_id": "..."}
"""

from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.tasks.process import process_sensor_event

router = APIRouter()


class SensorWebhookPayload(BaseModel):
    sensor_id: str = Field(..., examples=["sensor-01"])
    location: str = Field(..., examples=["Склад А"])
    temperature: float = Field(..., examples=[52.3])
    humidity: float = Field(..., examples=[45.0])
    # ISO 8601, например: 2026-03-04T10:30:00Z
    timestamp: datetime


@router.post("/sensor")
async def post_sensor(payload: SensorWebhookPayload):
    # Celery с JSON-сериализацией: datetime приводим к строке (ISO 8601).
    timestamp_utc = payload.timestamp.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

    task = process_sensor_event.apply_async(
        kwargs={
            "sensor_id": payload.sensor_id,
            "location": payload.location,
            "temperature": payload.temperature,
            "humidity": payload.humidity,
            "timestamp": timestamp_utc,
        }
    )
    return {"status": "accepted", "task_id": task.id}
