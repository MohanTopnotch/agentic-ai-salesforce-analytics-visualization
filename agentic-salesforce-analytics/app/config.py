from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "Agentic AI Salesforce Analytics"
    app_env: str = "local"
    api_prefix: str = "/api/v1"
    data_source_mode: str = "mock"
    log_level: str = "INFO"
    soql_timeout_seconds: int = 5
    soql_max_repair_attempts: int = 3
    max_query_rows: int = 2000
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

@lru_cache
def get_settings() -> Settings:
    return Settings()
