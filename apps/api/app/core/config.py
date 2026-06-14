from functools import lru_cache
from pydantic_setting import BaseSetting,SettingConfigDict


class Settings(BaseSettings):
    environment: str="development"
    
    database_url:str
    redis_url:str
    
    urbankart_base_url:str="http://localhost:8001"
    urbankart_api_key: str="dev_urbankaert_key"
    
    model_config=SettingConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
        )
    
@lru_cache()
def get_settings() -> Settings:
    return Settings()