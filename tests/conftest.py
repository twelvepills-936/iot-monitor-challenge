from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import pytest
import httpx
from httpx import ASGITransport


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"

# Убедимся, что правила `rules.json` и импорт модуля `app.*` работают.
os.chdir(ROOT_DIR)
sys.path.insert(0, str(BACKEND_DIR))

# Чтобы unit-тесты не падали из-за alembic/базы, миграции можно пропускать.
os.environ.setdefault("SKIP_MIGRATIONS", "1")


@pytest.fixture(scope="session")
def fastapi_app():
    from app.main import app as app_main

    return app_main


@pytest.fixture
def client(fastapi_app):
    """
    Синхронный клиент поверх httpx ASGITransport (без requests/TestClient).
    Возвращает объект с методом .post(...), который работает синхронно.
    """

    transport = ASGITransport(app=fastapi_app)
    base_url = "http://test"

    class _Client:
        def post(self, path: str, json=None):
            async def _do():
                async with httpx.AsyncClient(transport=transport, base_url=base_url) as ac:
                    return await ac.post(path, json=json)

            return asyncio.run(_do())

    return _Client()
