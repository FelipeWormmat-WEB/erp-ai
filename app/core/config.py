from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: Literal["development", "test", "production"] = "development"
    demo_mode: bool = False
    database_url: str
    redis_url: str
    cache_ttl_seconds: int = Field(default=60, ge=1, le=3600)
    redis_timeout_seconds: float = Field(default=0.2, gt=0, le=5)
    jwt_secret: str = Field(min_length=32)
    access_token_expire_minutes: int = Field(default=30, ge=1, le=1440)
    seed_username: str = Field(min_length=3, max_length=50)
    seed_password: str = Field(min_length=8)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        if not value.startswith("postgresql+asyncpg://"):
            raise ValueError("DATABASE_URL deve usar postgresql+asyncpg")
        return value

    @field_validator("redis_url")
    @classmethod
    def validate_redis_url(cls, value: str) -> str:
        if not value.startswith(("redis://", "rediss://")):
            raise ValueError("REDIS_URL deve usar redis:// ou rediss://")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
