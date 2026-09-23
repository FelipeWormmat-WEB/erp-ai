from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: Literal["development", "test", "production"] = "development"
    database_url: str
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
        print(f"Validating DATABASE_URL: {value}")
        if not value.startswith("postgresql+asyncpg://"):
            raise ValueError("DATABASE_URL deve usar postgresql+asyncpg")
        return value


@lru_cache
def get_settings() -> Settings:
    print("Initializing settings...")
    return Settings()
