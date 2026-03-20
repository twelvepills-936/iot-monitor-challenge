import logging
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
