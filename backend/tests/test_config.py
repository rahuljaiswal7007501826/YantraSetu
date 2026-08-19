"""Production-hardening config tests (Phase 13.1).

These construct Settings() directly with explicit overrides (init args take
priority over the .env file), so they never depend on or mutate the real .env.
"""
import pytest
from pydantic import ValidationError

from app.config import Settings


def test_dev_settings_are_permissive():
    # cors_origins is passed explicitly so this test is deterministic regardless
    # of any CORS_ORIGINS set in the environment/.env (matches the sibling tests
    # and this file's docstring: use explicit overrides, never depend on .env).
    s = Settings(
        app_env="development",
        debug=True,
        secret_key="dev-only-secret-change-me",
        cors_origins="http://localhost:5173,http://localhost:3000",
    )
    assert s.is_production is False
    assert s.debug is True  # dev is left alone
    assert "http://localhost:5173" in s.cors_origins_list


def test_cors_origins_parsed_from_comma_string():
    s = Settings(cors_origins="https://a.com, https://b.com ,")
    assert s.cors_origins_list == ["https://a.com", "https://b.com"]


def test_production_rejects_placeholder_secret():
    with pytest.raises(ValidationError):
        Settings(app_env="production", secret_key="change-me-in-production")
    with pytest.raises(ValidationError):
        Settings(app_env="production", secret_key="dev-only-secret-change-me")


def test_production_rejects_short_secret():
    with pytest.raises(ValidationError):
        Settings(app_env="production", secret_key="short")


def test_production_forces_debug_off_with_strong_secret():
    s = Settings(app_env="production", debug=True, secret_key="x" * 48)
    assert s.is_production is True
    assert s.debug is False  # forced off in production
