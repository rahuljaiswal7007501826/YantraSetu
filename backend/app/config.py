"""
Application configuration.

We use pydantic-settings so every configuration value comes from environment
variables (loaded from a local `.env` file during development). This keeps
secrets out of the source code and lets the same code run in dev, demo, and
production just by changing environment values.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Tell pydantic-settings to read a `.env` file sitting next to where we
    # launch the app (the backend/ folder). Unknown keys are ignored so an
    # extra variable never crashes startup.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Core app metadata ---
    app_name: str = "YantraSetu API"
    app_env: str = "development"
    debug: bool = True

    # --- API ---
    api_v1_prefix: str = "/api"

    # --- Database (wired up in Phase 1) ---
    # Defaults to a local SQLite file so the app can boot before PostgreSQL is
    # connected. We switch to PostgreSQL via DATABASE_URL without code changes.
    database_url: str = "sqlite:///./yantrasetu.db"

    # --- Security (used from the auth phase) ---
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60 * 24  # 24 hours

    # --- CORS: which frontend origins may call this API ---
    # Kept as a code default (not read from .env) to avoid env list-parsing
    # pitfalls. Vite's dev server runs on port 5173.
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


@lru_cache
def get_settings() -> Settings:
    """Return a single cached Settings instance, parsed once and reused."""
    return Settings()
