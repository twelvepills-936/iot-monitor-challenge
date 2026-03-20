from __future__ import annotations

import asyncio
from logging.config import fileConfig
import sys
from pathlib import Path

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

# Alembic запускается из отдельного процесса, и PYTHONPATH может не включать
# корень проекта. Добавим его явно, чтобы импортировать пакет `app`.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.config import settings
from app.models.event import Base

# this is the Alembic Config object, which provides access to the values within
# the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
#
# В некоторых минимальных конфигурациях ini-файла могут отсутствовать секции,
# ожидаемые alembic (например, `formatters`). Логирование нам не критично для
# миграций, поэтому сделаем загрузку безопасной.
if config.config_file_name is not None:
    try:
        fileConfig(config.config_file_name)
    except Exception:
        # При ошибке конфигурации логов не останавливаем миграции.
        pass

# Set target metadata for 'autogenerate' support.
target_metadata = Base.metadata


def _get_sqlalchemy_url() -> str:
    # pydantic settings уже берёт DATABASE_URL из окружения (docker-compose).
    return settings.database_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = _get_sqlalchemy_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = _get_sqlalchemy_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(
            lambda sync_conn: context.configure(
                connection=sync_conn,
                target_metadata=target_metadata,
                compare_type=True,
            )
        )

        async with connection.begin():
            context.run_migrations()

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())

