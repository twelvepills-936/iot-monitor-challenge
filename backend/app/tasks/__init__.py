import logging
import os
import subprocess
from pathlib import Path

from celery import Celery
from celery.signals import worker_process_init

celery_app = Celery(
    "iot_monitor",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/1",
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
)

logger = logging.getLogger(__name__)


@worker_process_init.connect
def apply_alembic_migrations_on_worker_init(**_: object) -> None:
    """
    Миграции применяем на старте воркера, чтобы задачи могли сохранять события в БД.
    """

    if os.getenv("SKIP_MIGRATIONS", "").lower() in {"1", "true", "yes"}:
        logger.info("SKIP_MIGRATIONS is set; skipping alembic upgrade and creating tables via init_db()")
        from app.db import init_db

        import asyncio

        asyncio.run(init_db())
        return

    backend_root = Path(__file__).resolve().parents[2]
    alembic_ini = backend_root / "alembic.ini"

    try:
        subprocess.run(
            ["alembic", "-c", str(alembic_ini), "upgrade", "head"],
            cwd=str(backend_root),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
    except Exception:
        logger.exception("Failed to apply alembic migrations on celery worker startup")
        raise


# Важно: worker Celery не “подхватывает” задачи автоматически, если модуль с задачами
# не импортирован. Импортируем `process.py`, чтобы зарегистрировать `process_sensor_event`.
from app.tasks import process as _process  # noqa: F401,E402
