from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Collision Repair Order Summarizer API"
    app_env: str = "development"
    log_level: str = "INFO"
    openai_api_key: str | None = None
    openai_model: str = "gpt-5-mini"
    request_timeout_seconds: float = 30.0
    database_path: str = "data/repair_order_summary.db"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
