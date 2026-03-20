"""
API для получения списка событий.

TODO: Реализовать GET /api/events
- Возвращать список событий из PostgreSQL
- Поддержать фильтрацию: по severity, по sensor_id, по диапазону дат
- Пагинация (limit, offset)
- Сортировка по дате (новые первыми)
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.db import get_session, init_db
from app.models.event import SensorEvent

router = APIRouter()


@router.get("/events")
async def get_events(
    severity: str | None = Query(None, pattern="^(normal|warning|critical)$"),
    sensor_id: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    Возвращает события датчиков из PostgreSQL.
    """

    # На случай, если сервис поднялся без миграций (например, в тестах).
    await init_db()

    if date_from is not None and date_from.tzinfo is None:
        date_from = date_from.replace(tzinfo=timezone.utc)
    if date_to is not None and date_to.tzinfo is None:
        date_to = date_to.replace(tzinfo=timezone.utc)

    stmt = select(SensorEvent)

    if severity is not None:
        stmt = stmt.where(SensorEvent.severity == severity)
    if sensor_id is not None:
        stmt = stmt.where(SensorEvent.sensor_id == sensor_id)
    if date_from is not None:
        stmt = stmt.where(SensorEvent.created_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(SensorEvent.created_at <= date_to)

    stmt = (
        stmt.order_by(SensorEvent.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    async with get_session() as session:
        res = await session.execute(stmt)
        events = res.scalars().all()

    return [
        {
            "id": e.id,
            "sensor_id": e.sensor_id,
            "location": e.location,
            "temperature": e.temperature,
            "humidity": e.humidity,
            "severity": e.severity,
            "notification_sent": e.notification_sent,
            "error_message": e.error_message,
            "created_at": e.created_at,
        }
        for e in events
    ]
