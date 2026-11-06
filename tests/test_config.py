from __future__ import annotations

import pytest

from myanmar_dubber.config import MALE_VOICE, Settings
from myanmar_dubber.errors import ConfigurationError


def _required_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "telegram-test-token")
    monkeypatch.setenv("GROQ_API_KEY", "groq-test-token")


def test_default_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    _required_env(monkeypatch)
    monkeypatch.delenv("ALLOWED_USER_IDS", raising=False)
    monkeypatch.delenv("APP_MODE", raising=False)
    settings = Settings.from_env()
    assert settings.default_voice == MALE_VOICE
    assert settings.video_enhance is True
    assert settings.max_video_seconds == 180
    assert settings.max_output_bytes == 49 * 1024 * 1024
    assert settings.groq_base_url == "https://api.groq.com/openai/v1"
    assert settings.app_mode == "polling"
    assert len(settings.webhook_secret) == 64
    assert settings.is_user_allowed(12345)


def test_allowed_user_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    _required_env(monkeypatch)
    monkeypatch.setenv("ALLOWED_USER_IDS", "123, 456,123")
    settings = Settings.from_env()
    assert settings.allowed_user_ids == frozenset({123, 456})
    assert settings.is_user_allowed(123)
    assert not settings.is_user_allowed(999)


def test_webhook_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    _required_env(monkeypatch)
    monkeypatch.setenv("APP_MODE", "webhook")
    monkeypatch.setenv("WEBHOOK_URL", "https://example.onrender.com/")
    monkeypatch.setenv("WEBHOOK_SECRET", "test-secret")
    monkeypatch.setenv("PORT", "10000")
    settings = Settings.from_env()
    assert settings.app_mode == "webhook"
    assert settings.webhook_url == "https://example.onrender.com"
    assert settings.webhook_secret == "test-secret"
    assert settings.port == 10000


def test_render_external_url_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    _required_env(monkeypatch)
    monkeypatch.delenv("WEBHOOK_URL", raising=False)
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://auto.onrender.com")
    settings = Settings.from_env()
    assert settings.webhook_url == "https://auto.onrender.com"


def test_missing_telegram_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.setenv("GROQ_API_KEY", "groq-test-token")
    with pytest.raises(ConfigurationError, match="TELEGRAM_BOT_TOKEN"):
        Settings.from_env()


def test_missing_groq_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "telegram-test-token")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(ConfigurationError, match="GROQ_API_KEY"):
        Settings.from_env()


def test_invalid_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    _required_env(monkeypatch)
    monkeypatch.setenv("MAX_VIDEO_SECONDS", "zero")
    with pytest.raises(ConfigurationError, match="MAX_VIDEO_SECONDS"):
        Settings.from_env()
