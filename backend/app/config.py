"""
Application configuration.

We use pydantic-settings so every configuration value comes from environment
variables (loaded from a local `.env` file during development). This keeps
secrets out of the source code and lets the same code run in dev, demo, and
production just by changing environment values.

Production hardening (Phase 13.1): when APP_ENV=production the app refuses to
start with an insecure/placeholder SECRET_KEY, and DEBUG is forced off. CORS
origins are configurable via the CORS_ORIGINS environment variable.
"""
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Placeholder secrets that must never be used in production.
INSECURE_SECRET_KEYS = {
    "",
    "change-me-in-production",
    "dev-only-secret-change-me",
}
MIN_SECRET_KEY_LENGTH = 16


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
    algorithm: str = "HS256"  # JWT signing algorithm (HMAC-SHA256)

    # --- CORS: which frontend origins may call this API ---
    # Comma-separated string from the CORS_ORIGINS env var (kept as a string to
    # avoid pydantic's JSON-list parsing pitfalls). Parsed into a list by
    # `cors_origins_list`. Default covers Vite's dev server.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    # --- Voice input (Phase 17): Bhashini ASR. All optional - empty credentials
    # mean the voice feature simply falls back (Web Speech API, then manual text). ---
    bhashini_user_id: str = ""
    bhashini_api_key: str = ""  # ULCA "ulcaApiKey"
    bhashini_pipeline_id: str = "64392f96daac500b55c543cd"  # MeitY public ASR pipeline
    bhashini_config_url: str = (
        "https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline"
    )
    # Reject audio uploads larger than this (a few-second clip is far smaller).
    voice_max_upload_bytes: int = 8_000_000
    # How long to cache a TTS clip for an identical string. Confirmation/status
    # copy repeats a lot, so this avoids redundant Bhashini calls (per-process).
    voice_tts_cache_ttl_seconds: int = 300

    @property
    def cors_origins_list(self) -> list[str]:
        """CORS origins as a clean list (comma-split, trimmed, no blanks)."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def bhashini_configured(self) -> bool:
        """True only when both Bhashini credentials are present."""
        return bool(self.bhashini_user_id.strip() and self.bhashini_api_key.strip())

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() == "production"

    @model_validator(mode="after")
    def _harden_for_production(self) -> "Settings":
        """Fail safely on insecure production configuration.

        Development/demo behaviour is unchanged; these guards only apply when
        APP_ENV=production.
        """
        if self.is_production:
            # Never serve with debug on in production.
            self.debug = False
            # Refuse to boot with a placeholder or too-short secret key.
            if (
                self.secret_key in INSECURE_SECRET_KEYS
                or len(self.secret_key) < MIN_SECRET_KEY_LENGTH
            ):
                raise ValueError(
                    "Insecure SECRET_KEY for production. Set a strong random value, e.g.:\n"
                    '  python -c "import secrets; print(secrets.token_urlsafe(48))"'
                )
        return self


@lru_cache
def get_settings() -> Settings:
    """Return a single cached Settings instance, parsed once and reused."""
    return Settings()
