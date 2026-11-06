from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from telegram import Bot

from myanmar_dubber.config import Settings
from myanmar_dubber.web import create_web_app


def _settings(monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:TEST_TOKEN")
    monkeypatch.setenv("GROQ_API_KEY", "groq-test-token")
    monkeypatch.setenv("APP_MODE", "webhook")
    monkeypatch.setenv("WEBHOOK_URL", "https://example.onrender.com")
    return Settings.from_env()


def test_web_app_exposes_health_and_webhook_routes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_web_app(_settings(monkeypatch))
    paths = {route.path for route in app.routes}
    assert "/health" in paths
    assert "/telegram/webhook" in paths
    assert app.state.dubbing_service is not None


def test_web_lifecycle_health_and_webhook_security(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    app = create_web_app(_settings(monkeypatch))
    telegram_app = app.state.telegram_application
    service = app.state.dubbing_service
    webhook_calls: list[dict] = []

    async def no_op(*_args, **_kwargs) -> None:
        return None

    async def fake_set_webhook(_self, **kwargs) -> None:
        webhook_calls.append(kwargs)

    monkeypatch.setattr(telegram_app, "initialize", no_op)
    monkeypatch.setattr(telegram_app, "start", no_op)
    monkeypatch.setattr(telegram_app, "stop", no_op)
    monkeypatch.setattr(telegram_app, "shutdown", no_op)
    monkeypatch.setattr(service, "start", no_op)
    monkeypatch.setattr(service, "stop", no_op)
    monkeypatch.setattr(Bot, "set_webhook", fake_set_webhook)

    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"
        assert health.json()["webhook_configured"] is True
        unauthorized = client.post("/telegram/webhook", json={})
        assert unauthorized.status_code == 401

    assert webhook_calls[0]["url"] == (
        "https://example.onrender.com/telegram/webhook"
    )
    assert webhook_calls[0]["secret_token"]
