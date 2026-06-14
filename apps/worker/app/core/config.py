from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    environment: str = "development"

    celery_broker_url: str
    celery_result_backend: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_worker_settings() -> WorkerSettings:
    return WorkerSettings()