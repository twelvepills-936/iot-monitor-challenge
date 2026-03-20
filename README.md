# IoT Monitor — Тестовое задание

## Легенда

Компания управляет сетью IoT-датчиков на промышленных объектах (склады, серверные, теплицы). Датчики измеряют температуру и влажность и отправляют данные через HTTP.

Нужен сервис, который принимает показания, классифицирует их по серьёзности, отправляет уведомления при критических значениях и показывает всё на дашборде.

## Что уже есть

Готовый scaffolding проекта:

```
iot-monitor/
├── docker-compose.yml          ← настроен, поднимает все сервисы
├── rules.json                  ← конфиг правил (пороги температуры/влажности)
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py             ← FastAPI приложение (готово)
│   │   ├── config.py           ← настройки (готово)
│   │   ├── api/
│   │   │   ├── webhooks.py     ← TODO
│   │   │   └── events.py       ← TODO
│   │   ├── tasks/
│   │   │   ├── __init__.py     ← Celery конфиг (готово)
│   │   │   └── process.py      ← TODO
│   │   └── models/
│   │       └── event.py        ← TODO
├── mock-telegram/
│   ├── Dockerfile
│   └── app.py                  ← TODO
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   └── src/
│       └── App.jsx             ← TODO
└── tests/
    ├── conftest.py             ← TODO
    └── test_webhook.py         ← TODO
```

## Требования к окружению

- Docker Desktop (Windows / Mac / Linux)
- Git
- Больше ничего не нужно — всё работает в контейнерах

## Задача

### 1. Webhook-эндпоинт

Файл: `backend/app/api/webhooks.py`

Реализуй `POST /webhooks/sensor`:
- Принимает JSON:
  ```json
  {
    "sensor_id": "sensor-01",
    "location": "Склад А",
    "temperature": 52.3,
    "humidity": 45.0,
    "timestamp": "2026-03-04T10:30:00Z"
  }
  ```
- Валидация через Pydantic
- Отправляет задачу в Celery-очередь (не обрабатывает синхронно!)
- Возвращает `{"status": "accepted", "task_id": "..."}`

### 2. Celery-задача

Файл: `backend/app/tasks/process.py`

Реализуй задачу `process_sensor_event`:
- Загружает правила из `rules.json`
- Определяет severity:
  - `temperature > 50` или `humidity > 95` → **critical**
  - `temperature > 35` или `humidity > 80` → **warning**
  - Иначе → **normal**
- Если **critical** — отправляет уведомление в Telegram (mock API):
  ```
  POST http://mock-telegram:8001/bot{token}/sendMessage
  {"chat_id": "123456", "text": "🚨 CRITICAL: sensor-01 (Склад А) — 52.3°C"}
  ```
- Сохраняет событие в PostgreSQL
- При ошибке Telegram — retry до 3 раз с экспоненциальной задержкой

### 3. Модель БД

Файл: `backend/app/models/event.py`

SQLAlchemy модель `SensorEvent`:
- `id` — primary key
- `sensor_id` — str
- `location` — str
- `temperature` — float
- `humidity` — float
- `severity` — str (normal / warning / critical)
- `notification_sent` — bool
- `error_message` — str, nullable
- `created_at` — datetime

Настрой Alembic для миграций. Миграция должна применяться при старте.

### 4. API событий

Файл: `backend/app/api/events.py`

Реализуй `GET /api/events`:
- Возвращает список событий из БД
- Фильтрация: `severity`, `sensor_id`, `date_from`, `date_to`
- Пагинация: `limit` (default 50), `offset` (default 0)
- Сортировка: новые первыми

### 5. Mock Telegram

Файл: `mock-telegram/app.py`

Фейковый Telegram Bot API:
- `POST /bot{token}/sendMessage` — принимает `chat_id` и `text`, сохраняет в память
- `GET /bot{token}/messages` — возвращает список всех отправленных сообщений
- **10% запросов** `sendMessage` возвращают HTTP 500 (имитация сбоя)

### 6. React-дашборд

Файл: `frontend/src/App.jsx`

Страница мониторинга:
- **Карточки сверху:** всего событий, critical за сегодня, последнее событие
- **Таблица событий:** время, sensor_id, location, temperature, humidity, severity, notification_sent
- **Цвета строк:** normal — зелёный, warning — жёлтый, critical — красный
- **Фильтры:** по severity, по sensor_id
- **Автообновление** каждые 3 секунды (polling `GET /api/events`)
- **Кнопка "Симулировать датчик"** — форма с полями sensor_id, location, temperature, humidity → отправляет `POST /webhooks/sensor`

UI должен быть аккуратным. Можно использовать любую библиотеку (Tailwind, MUI, Ant Design) или чистый CSS.

### 7. Docker Compose

`docker-compose.yml` уже настроен. После твоих изменений команда:

```bash
docker-compose up --build
```

должна поднять всё и всё должно работать:
- `http://localhost:8000/docs` — Swagger API
- `http://localhost:8000/health` — healthcheck
- `http://localhost:3000` — React-дашборд
- `http://localhost:8001/docs` — Mock Telegram API

### 8. Тесты

Файлы: `tests/conftest.py`, `tests/test_webhook.py`

Напиши тесты (pytest):
- Отправка валидного webhook → 200 + task_id
- Отправка невалидных данных → 422
- Celery-задача: успешная обработка, запись в БД
- Celery-задача: retry при ошибке Telegram
- Правильная классификация severity по rules.json

## Что оценивается

| Критерий | Вес |
|---|---|
| **Работает из коробки** — `docker-compose up --build` и всё поднялось | 30% |
| **Функциональность** — webhook → celery → DB → UI, цепочка работает | 30% |
| **Качество кода** — структура, читаемость, Pydantic-схемы, error handling | 20% |
| **Тесты** — покрытие основных сценариев | 10% |
| **Git-история** — осмысленные коммиты, не один коммит "всё" | 10% |

## Бонус (необязательно, но плюс)

- Retry с экспоненциальной задержкой при недоступности Telegram
- Structured logging (structlog / loguru)
- Фильтрация по диапазону дат в React UI
- Отображение статистики (графики)

## Как делать

1. Форкни этот репозиторий
2. Создай ветку `feature/iot-monitor`
3. Пиши код, коммить по мере выполнения
4. Создай Pull Request с описанием:
   - Что реализовал
   - Сколько времени потратил
   - Какие инструменты использовал (AI, документация, статьи)
5. Будь готов объяснить любую строку своего кода на собеседовании

## Срок

**3 дня** с момента получения задания.

## Важно

- **Можно и нужно** использовать AI-инструменты (Claude, ChatGPT, Cursor и т.д.)
- Важно не просто скопировать — а **понимать** что написано. На собеседовании спросим
- Если что-то непонятно — разберись сам, это часть задания
- Не нужно делать идеально — нужно сделать **работающий результат**
