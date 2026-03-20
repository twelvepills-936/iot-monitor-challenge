import logging
import asyncio
import os
import subprocess
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.webhooks import router as webhook_router
from app.api.events import router as events_router

app = FastAPI(
    title="IoT Monitor",
    version="0.1.0",
    description="IoT sensor monitoring service — test task",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhook_router, prefix="/webhooks", tags=["webhooks"])
app.include_router(events_router, prefix="/api", tags=["events"])

logger = logging.getLogger(__name__)


@app.on_event("startup")
async def apply_alembic_migrations() -> None:
    """
    Миграции должны применяться при старте сервиса.
    Это гарантирует наличие таблицы для Celery-заданий и API.
    """

    if os.getenv("SKIP_MIGRATIONS", "").lower() in {"1", "true", "yes"}:
        logger.info("SKIP_MIGRATIONS is set; skipping alembic upgrade and creating tables via init_db()")
        from app.db import init_db

        await init_db()
        return

    backend_root = Path(__file__).resolve().parents[1]
    alembic_ini = backend_root / "alembic.ini"

    await asyncio.to_thread(
        subprocess.run,
        ["alembic", "-c", str(alembic_ini), "upgrade", "head"],
        {
            "cwd": str(backend_root),
            "check": True,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.STDOUT,
            "text": True,
        },
    )


@app.get("/health")
async def health():
    return {"status": "ok"}
