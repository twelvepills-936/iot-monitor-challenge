"""
SQLAlchemy модель для хранения событий датчиков.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SensorEvent(Base):
    __tablename__ = "sensor_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    sensor_id: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str] = mapped_column(String(255), nullable=False)

    temperature: Mapped[float] = mapped_column(Float, nullable=False)
    humidity: Mapped[float] = mapped_column(Float, nullable=False)

    severity: Mapped[str] = mapped_column(String(16), nullable=False)  # normal / warning / critical

    notification_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error_message: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    # В тестах удобно хранить время события как пришло от датчика.
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
