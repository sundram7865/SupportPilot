from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    environment: str = Field(default="development")

    database_url: str
    redis_url: str

    celery_broker_url: str
    celery_result_backend: str

    urbankart_base_url: str = "http://localhost:8001"
    urbankart_api_key: str = "dev_urbankart_key"

    dev_auth_enabled: bool = True

    clerk_issuer: str | None = None
    clerk_jwks_url: str | None = None

    integration_secret_key: str

    ai_provider: str = "mock"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-1.5-flash"
    cloudinary_cloud_name: str | None = None
    cloudinary_api_key: str | None = None
    cloudinary_api_secret: str | None = None

    sentry_dsn: str | None = None

    cors_allowed_origins: str = (
        "http://localhost:3000,http://127.0.0.1:3000"
    )
    rate_limit_enabled: bool = True
    public_read_rate_limit_per_minute: int = 60
    public_write_rate_limit_per_minute: int = 10
    external_api_rate_limit_per_minute: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}

    @property
    def cors_origins_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_allowed_origins.split(",")
            if origin.strip()
        ]

    @model_validator(mode="after")
    def validate_security_settings(self):
        if self.is_production:
            if self.dev_auth_enabled:
                raise ValueError(
                    "DEV_AUTH_ENABLED must be false in production."
                )

            if not self.clerk_issuer:
                raise ValueError(
                    "CLERK_ISSUER is required in production."
                )

            if not self.clerk_jwks_url:
                raise ValueError(
                    "CLERK_JWKS_URL is required in production."
                )

            if self.ai_provider == "gemini" and not self.gemini_api_key:
                raise ValueError(
                    "GEMINI_API_KEY is required when AI_PROVIDER=gemini."
                )

            if self.integration_secret_key in {
                "dev",
                "changeme",
                "change-me",
                "secret",
                "dev-secret",
            }:
                raise ValueError(
                    "INTEGRATION_SECRET_KEY must be strong in production."
                )

            if not self.cors_origins_list:
                raise ValueError(
                    "CORS_ALLOWED_ORIGINS must contain at least one origin in production."
                )

            if "*" in self.cors_origins_list:
                raise ValueError(
                    "Wildcard CORS origin '*' is not allowed in production."
                )

            for origin in self.cors_origins_list:
                if origin.startswith("http://localhost") or origin.startswith(
                    "http://127.0.0.1"
                ):
                    raise ValueError(
                        "Localhost CORS origins are not allowed in production."
                    )

        return self


@lru_cache()
def get_settings() -> Settings:
    return Settings()