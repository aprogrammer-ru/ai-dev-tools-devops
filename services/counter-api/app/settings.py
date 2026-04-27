from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "counter-api"
    app_env: str = "dev"
    app_version: str = "0.1.0"

    postgres_dsn: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/counter"
    redis_url: str = "redis://redis:6379/0"

    idempotency_ttl_seconds: int = 3600
    rate_limit_window_seconds: int = 60
    rate_limit_max_requests: int = 120

    log_level: str = "INFO"
    metrics_enabled: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
