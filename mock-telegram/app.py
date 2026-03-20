"""
Mock Telegram Bot API.

Фейковый Telegram Bot API:
- POST /bot{token}/sendMessage — принимает chat_id и text, сохраняет в память
- GET /bot{token}/messages — возвращает список всех отправленных сообщений

10% запросов sendMessage возвращают HTTP 500 (имитация сбоя).
"""

import random
from datetime import datetime, timezone
from threading import Lock

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Mock Telegram Bot API")

_messages_by_token: dict[str, list[dict]] = {}
_lock = Lock()


class SendMessagePayload(BaseModel):
    chat_id: str
    text: str


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/bot{token}/sendMessage")
async def send_message(token: str, payload: SendMessagePayload):
    # 10% — имитируем сбой.
    if random.random() < 0.1:
        raise HTTPException(status_code=500, detail="Mock Telegram failure")

    message = {
        "chat_id": payload.chat_id,
        "text": payload.text,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }

    with _lock:
        _messages_by_token.setdefault(token, []).append(message)

    return {"ok": True, "result": message}


@app.get("/bot{token}/messages")
async def get_messages(token: str):
    with _lock:
        return {"ok": True, "messages": list(_messages_by_token.get(token, []))}
