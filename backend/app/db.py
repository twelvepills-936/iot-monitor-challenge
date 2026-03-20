from __future__ import annotations

from app.config import settings
from app.models.event import Base

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


engine = create_async_engine(settings.database_url, pool_pre_ping=True, future=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    # В проекте описаны миграции через Alembic, но для тестового задания достаточно
    # гарантировать наличие таблицы при старте/обработке задач.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

