from __future__ import annotations

import logging
import shutil

from telegram import Update

from .bot import create_application
from .config import Settings
from .errors import ConfigurationError


def main() -> None:
    try:
        settings = Settings.from_env()
    except ConfigurationError as exc:
        raise SystemExit(f"Configuration error: {exc}") from exc

    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    for executable in ("ffmpeg", "ffprobe"):
        if not shutil.which(executable):
            raise SystemExit(
                f"Configuration error: {executable} is required. "
                "Install FFmpeg or use the supplied Docker setup."
            )
    if settings.ytdlp_cookies_file and not settings.ytdlp_cookies_file.is_file():
        raise SystemExit("Configuration error: YTDLP_COOKIES_FILE does not exist.")

    try:
        settings.work_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise SystemExit(f"Configuration error: cannot create WORK_DIR: {exc}") from exc

    application = create_application(settings)
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
