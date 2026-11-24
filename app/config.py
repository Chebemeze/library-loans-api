from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables or a local .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg://gamp:gamp@127.0.0.1:5432/library"
    test_database_url: str | None = None

    loan_period_days: int = 14
    loan_limit_per_member: int = 3
    fine_per_late_day_kobo: int = 50
    fine_cap_per_loan_kobo: int = Field(default=2000, ge=0, le=2000)


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
