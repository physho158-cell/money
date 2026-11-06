from __future__ import annotations

import pytest

from myanmar_dubber.config import FEMALE_VOICE, Settings
from myanmar_dubber.errors import ConfigurationError


def _required_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "telegram-test-token")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-test-token")


def test_default_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    _required_env(monkeypatch)
    monkeypatch.delenv("ALLOWED_USER_IDS", raising=False)
    settings = Settings.from_env()
    assert settings.default_voice == FEMALE_VOICE
    assert settings.max_video_seconds == 180
    assert settings.max_output_bytes == 49 * 1024 * 1024
    assert settings.is_user_allowed(12345)


def test_allowed_user_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    _required_env(monkeypatch)
    monkeypatch.setenv("ALLOWED_USER_IDS", "123, 456,123")
    settings = Settings.from_env()
    assert settings.allowed_user_ids == frozenset({123, 456})
    assert settings.is_user_allowed(123)
    assert not settings.is_user_allowed(999)


def test_missing_telegram_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "openai-test-token")
    with pytest.raises(ConfigurationError, match="TELEGRAM_BOT_TOKEN"):
        Settings.from_env()


def test_invalid_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    _required_env(monkeypatch)
    monkeypatch.setenv("MAX_VIDEO_SECONDS", "zero")
    with pytest.raises(ConfigurationError, match="MAX_VIDEO_SECONDS"):
        Settings.from_env()
