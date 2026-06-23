from functools import lru_cache
from pydantic_settings import BaseSettings,SettingsConfigDict


class Settings(BaseSettings):
    environment: str="development"
    
    database_url:str
    redis_url:str
    
    urbankart_base_url:str="http://localhost:8001"
    urbankart_api_key: str = "dev_urbankart_key"
    dev_auth_enabled: bool = True
    integration_secret_key: str
    clerk_issuer: str | None = None
    clerk_jwks_url: str | None = None
    ai_provider: str = "mock"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-1.5-flash"
    model_config=SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
        )
    
@lru_cache()
def get_settings() -> Settings:
    return Settings()