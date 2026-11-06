from __future__ import annotations

import asyncio
from pathlib import Path
from urllib.parse import urlsplit

import yt_dlp

from .errors import UserFacingError


def is_supported_youtube_url(value: str) -> bool:
    try:
        parsed = urlsplit(value.strip())
    except ValueError:
        return False
    if parsed.scheme not in {"http", "https"} or parsed.username or parsed.password:
        return False
    host = (parsed.hostname or "").lower().rstrip(".")
    is_youtube = host == "youtube.com" or host.endswith(".youtube.com")
    is_short_host = host == "youtu.be" or host.endswith(".youtu.be")
    if is_short_host:
        return bool(parsed.path.strip("/"))
    if not is_youtube:
        return False
    return (
        parsed.path.startswith("/shorts/")
        or parsed.path.startswith("/watch")
        or parsed.path.startswith("/live/")
        or parsed.path.startswith("/embed/")
    )


class YouTubeDownloader:
    def __init__(
        self,
        max_duration: int,
        max_bytes: int,
        cookies_file: Path | None = None,
    ) -> None:
        self.max_duration = max_duration
        self.max_bytes = max_bytes
        self.cookies_file = cookies_file

    def _options(self, directory: Path) -> dict:
        options = {
            "format": (
                "best[height<=720][ext=mp4]/best[height<=720]/"
                "best[ext=mp4]/best"
            ),
            "outtmpl": str(directory / "source.%(ext)s"),
            "noplaylist": True,
            "merge_output_format": "mp4",
            "max_filesize": self.max_bytes,
            "quiet": True,
            "no_warnings": True,
            "retries": 3,
            "socket_timeout": 30,
            "overwrites": True,
        }
        if self.cookies_file:
            options["cookiefile"] = str(self.cookies_file)
        return options

    def _metadata(self, url: str, directory: Path) -> dict:
        with yt_dlp.YoutubeDL(self._options(directory)) as ydl:
            info = ydl.extract_info(url, download=False)
        return info

    def _download(self, url: str, directory: Path) -> None:
        with yt_dlp.YoutubeDL(self._options(directory)) as ydl:
            ydl.extract_info(url, download=True)

    async def download(self, url: str, directory: Path) -> Path:
        try:
            info = await asyncio.to_thread(self._metadata, url, directory)
        except yt_dlp.utils.DownloadError as exc:
            raise UserFacingError(
                "YouTube ဗီဒီယိုအချက်အလက် ရယူ၍မရပါ။ Link မှန်ကန်ကြောင်းและ video ကို "
                "public ကြည့်ရှုနိုင်ကြောင်း စစ်ဆေးပါ။"
            ) from exc

        if info.get("is_live"):
            raise UserFacingError("Live stream အစား ပြီးဆုံးပြီးသား YouTube video ကို ပေးပို့ပါ။")
        duration = info.get("duration")
        if duration is None:
            raise UserFacingError("ဤဗီဒီယို၏ ကြာချိန်ကို စစ်ဆေး၍မရသဖြင့် ဒေါင်းလုဒ်လုပ်မည့်အစား ရပ်ထားပါတယ်။")
        if float(duration) > self.max_duration + 0.5:
            raise UserFacingError(
                f"ဗီဒီယိုကြာချိန်ကို {self.max_duration} စက္ကန့်အထိသာ လက်ခံပါတယ်။"
            )

        try:
            await asyncio.to_thread(self._download, url, directory)
        except yt_dlp.utils.DownloadError as exc:
            raise UserFacingError(
                "YouTube က ဤ server မှ ဒေါင်းလုဒ်လုပ်ခွင့်ကို ပိတ်ပင်နေနိုင်ပါတယ်။ "
                "Link အသစ်ဖြင့် ထပ်စမ်းပါ သို့မဟုတ် video ကို Telegram တွင် တင်ပေးပါ။"
            ) from exc

        candidates = [
            path
            for path in directory.glob("source.*")
            if path.is_file() and path.suffix not in {".part", ".ytdl", ".json"}
        ]
        if not candidates:
            raise UserFacingError("ဒေါင်းလုဒ်လုပ်ပြီးသော ဗီဒီယိုဖိုင်ကို ရှာမတွေ့ပါ။")
        source = max(candidates, key=lambda path: path.stat().st_size)
        if source.stat().st_size > self.max_bytes:
            raise UserFacingError("ဗီဒီယိုဖိုင်သည် Bot ၏ ဒေါင်းလုဒ် အရွယ်အစား ကန့်သတ်ချက်ထက် ကြီးနေပါတယ်။")
        return source
