from __future__ import annotations

from contextlib import asynccontextmanager

from app.config import settings
from app.models.event import Base

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


def _make_engine():
    # Engine привязывается к конкретному event-loop (asyncpg).
    # Поэтому не храним его глобально: при выполнении в разных loops создаём заново.
    return create_async_engine(settings.database_url, pool_pre_ping=True, future=True)


@asynccontextmanager
async def get_session():
    engine = _make_engine()
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    try:
        async with SessionLocal() as session:
            yield session
    finally:
        await engine.dispose()


async def init_db() -> None:
    # Для тестового задания достаточно гарантировать наличие таблиц.
    engine = _make_engine()
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    finally:
        await engine.dispose()

