from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from .errors import ConfigurationError

FEMALE_VOICE = "my-MM-NilarNeural"
MALE_VOICE = "my-MM-ThihaNeural"
SUPPORTED_VOICES = frozenset({FEMALE_VOICE, MALE_VOICE})


def _positive_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer.") from exc
    if value <= 0:
        raise ConfigurationError(f"{name} must be greater than zero.")
    return value


def _allowed_user_ids(raw: str) -> frozenset[int]:
    if not raw.strip():
        return frozenset()
    try:
        return frozenset(int(item.strip()) for item in raw.split(",") if item.strip())
    except ValueError as exc:
        raise ConfigurationError(
            "ALLOWED_USER_IDS must contain comma-separated numeric IDs."
        ) from exc


@dataclass(frozen=True, slots=True)
class Settings:
    telegram_bot_token: str
    openai_api_key: str
    openai_base_url: str | None
    whisper_model: str
    translation_model: str
    default_voice: str
    tts_rate: str
    max_video_seconds: int
    max_download_bytes: int
    max_output_bytes: int
    max_queue_size: int
    workers: int
    work_dir: Path
    ffmpeg_timeout_seconds: int
    allowed_user_ids: frozenset[int]
    ytdlp_cookies_file: Path | None
    log_level: str

    @classmethod
    def from_env(cls) -> Settings:
        load_dotenv()
        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not token:
            raise ConfigurationError("TELEGRAM_BOT_TOKEN is required.")
        if not api_key:
            raise ConfigurationError("OPENAI_API_KEY is required.")

        default_voice = os.getenv("DEFAULT_VOICE", FEMALE_VOICE).strip()
        if default_voice not in SUPPORTED_VOICES:
            raise ConfigurationError(
                f"DEFAULT_VOICE must be one of: {', '.join(sorted(SUPPORTED_VOICES))}."
            )

        cookies = os.getenv("YTDLP_COOKIES_FILE", "").strip() or None
        max_video_seconds = _positive_int("MAX_VIDEO_SECONDS", 180)
        max_download_mb = _positive_int("MAX_DOWNLOAD_MB", 100)
        max_output_mb = _positive_int("MAX_OUTPUT_MB", 49)

        return cls(
            telegram_bot_token=token,
            openai_api_key=api_key,
            openai_base_url=os.getenv("OPENAI_BASE_URL", "").strip() or None,
            whisper_model=os.getenv("WHISPER_MODEL", "whisper-1").strip(),
            translation_model=os.getenv("TRANSLATION_MODEL", "gpt-4o-mini").strip(),
            default_voice=default_voice,
            tts_rate=os.getenv("TTS_RATE", "+0%").strip(),
            max_video_seconds=max_video_seconds,
            max_download_bytes=max_download_mb * 1024 * 1024,
            max_output_bytes=max_output_mb * 1024 * 1024,
            max_queue_size=_positive_int("MAX_QUEUE_SIZE", 20),
            workers=_positive_int("WORKERS", 1),
            work_dir=Path(os.getenv("WORK_DIR", "/tmp/myanmar-dubber")).expanduser(),
            ffmpeg_timeout_seconds=_positive_int("FFMPEG_TIMEOUT_SECONDS", 900),
            allowed_user_ids=_allowed_user_ids(os.getenv("ALLOWED_USER_IDS", "")),
            ytdlp_cookies_file=Path(cookies).expanduser() if cookies else None,
            log_level=os.getenv("LOG_LEVEL", "INFO").upper().strip(),
        )

    def is_user_allowed(self, user_id: int) -> bool:
        return not self.allowed_user_ids or user_id in self.allowed_user_ids
