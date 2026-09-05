import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "NetOps Copilot AI Backend"
    API_V1_STR: str = "/api"
    DATABASE_URL: str = "sqlite:///./netops.db"
    COLLECTOR_SECRET: str = "netops-collector-secret-key-2026"
    ENVIRONMENT: str = "development"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

# Normalize Postgres connection strings if needed for SQLAlchemy 2.0+
if settings.DATABASE_URL.startswith("postgres://"):
    settings.DATABASE_URL = settings.DATABASE_URL.replace("postgres://", "postgresql://", 1)
