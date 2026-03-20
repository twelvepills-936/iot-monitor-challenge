"""
Тесты для webhook-эндпоинта и Celery-задач.

TODO: Реализовать тесты:
1. test_webhook_valid_data — отправка корректных данных, ожидаем 200 + task_id
2. test_webhook_invalid_data — отправка без обязательных полей, ожидаем 422
3. test_process_event_success — Celery-задача успешно обрабатывает событие
4. test_process_event_telegram_retry — Celery-задача делает retry при ошибке Telegram
5. test_severity_classification — правильное определение severity по rules.json
"""
