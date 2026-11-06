from __future__ import annotations

import logging
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from telegram import Update

from .bot import TelegramDubbingBot, create_application
from .config import Settings

logger = logging.getLogger(__name__)
_WEBHOOK_PATH = "/telegram/webhook"


def create_web_app(settings: Settings) -> FastAPI:
    telegram_app = create_application(settings)
    service = telegram_app.bot_data["dubbing_service"]
    if not isinstance(service, TelegramDubbingBot):
        raise TypeError("Dubbing service was not registered correctly.")

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        service_started = False
        telegram_started = False
        await telegram_app.initialize()
        try:
            await service.start(telegram_app)
            service_started = True
            await telegram_app.start()
            telegram_started = True
            if settings.webhook_url:
                await telegram_app.bot.set_webhook(
                    url=f"{settings.webhook_url}{_WEBHOOK_PATH}",
                    secret_token=settings.webhook_secret,
                    allowed_updates=Update.ALL_TYPES,
                    drop_pending_updates=False,
                )
                logger.info("Telegram webhook registered at %s", settings.webhook_url)
            else:
                logger.warning(
                    "WEBHOOK_URL is not set; health checks will pass but Telegram "
                    "webhook registration is skipped."
                )
            yield
        finally:
            if service_started:
                await service.stop(telegram_app)
            if telegram_started:
                await telegram_app.stop()
            await telegram_app.shutdown()

    app = FastAPI(title="Myanmar Video Dubber", lifespan=lifespan)
    app.state.telegram_application = telegram_app
    app.state.dubbing_service = service

    @app.get("/")
    @app.get("/health")
    async def health() -> dict[str, object]:
        return {
            "status": "ok",
            "webhook_configured": bool(settings.webhook_url),
            "mode": "webhook",
        }

    @app.post(_WEBHOOK_PATH)
    async def telegram_webhook(request: Request) -> dict[str, bool]:
        supplied_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if not secrets.compare_digest(supplied_secret, settings.webhook_secret):
            raise HTTPException(status_code=401, detail="Invalid webhook secret.")
        try:
            payload = await request.json()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid JSON.") from exc
        update = Update.de_json(payload, telegram_app.bot)
        if update is None:
            raise HTTPException(status_code=400, detail="Invalid Telegram update.")
        await telegram_app.process_update(update)
        return {"ok": True}

    return app


def run_webhook_server(settings: Settings) -> None:
    uvicorn.run(
        create_web_app(settings),
        host="0.0.0.0",
        port=settings.port,
        log_level="info",
        access_log=False,
    )
