"""
Mock Telegram Bot API.

TODO: Реализовать фейковый Telegram Bot API
- POST /bot{token}/sendMessage — принимает chat_id и text, сохраняет в память
- GET /bot{token}/messages — возвращает список отправленных сообщений (для отладки)
- 10% запросов sendMessage должны возвращать 500 (имитация сбоя)

Подсказка: используй FastAPI, случайные ошибки через random.random()
"""

from fastapi import FastAPI

app = FastAPI(title="Mock Telegram Bot API")


# TODO: реализовать эндпоинты
@app.get("/health")
async def health():
    return {"status": "ok"}
