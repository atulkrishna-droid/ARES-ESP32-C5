"""ARES Platform Configuration."""
from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    PROJECT_NAME: str = "ARES Platform"
    API_V1_STR: str = "/api/v1"

    # Database
    # Default to local sqlite for instant zero-dependency testing, can point to PostgreSQL via .env
    DATABASE_URL: str = "sqlite:///./ares.db"

    # Cryptography & Security
    JWT_SECRET: str = "super-secret-ares-cryptographic-signing-key-change-in-production-min-32-chars"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    @property
    def JWT_SECRET_KEY(self) -> str:
        return self.JWT_SECRET

    # Evidence Storage
    EVIDENCE_STORAGE_PATH: str = "./data/evidence"
    MAX_EVIDENCE_SIZE_MB: int = 100

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # Optional Redis
    REDIS_URL: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow",
    )


settings = Settings()
