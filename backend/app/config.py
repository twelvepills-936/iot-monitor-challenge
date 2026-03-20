from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/iot_monitor"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Telegram Bot (mock)
    telegram_bot_token: str = "fake-bot-token"
    telegram_chat_id: str = "123456"
    telegram_api_url: str = "http://mock-telegram:8001"

    class Config:
        env_file = ".env"


settings = Settings()
