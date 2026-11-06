from __future__ import annotations

import asyncio
import logging
import shutil
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from telegram import BotCommand, Update
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from .config import FEMALE_VOICE, MALE_VOICE, Settings
from .downloader import is_supported_youtube_url
from .errors import UserFacingError
from .pipeline import DubbingPipeline

logger = logging.getLogger(__name__)

_START_TEXT = """မင်္ဂလာပါ 👋 မြန်မာ Video Dubbing Bot ဖြစ်ပါတယ်။

YouTube Shorts / YouTube video link (သို့) video file ကို ဒီမှာ ပို့လိုက်ပါ။
1️⃣ မူရင်းအသံကို transcript လုပ်ပါမယ်
2️⃣ မြန်မာစကားပြေအဖြစ် ဘာသာပြန်ပါမယ်
3️⃣ မူရင်းအသံအားလုံးကို ဖယ်ပြီး မြန်မာ AI အသံအသစ် ထည့်ပေးပါမယ်

/voice male — အမျိုးသားအသံ
/voice female — အမျိုးသမီးအသံ
/help — အသုံးပြုနည်း

တစ်ခါတည်း ဗီဒီယိုတစ်ခုသာ လုပ်ဆောင်နိုင်ပြီး၊ API ကုန်ကျစရိတ်ကို ထိန်းရန် ကြာချိန်ကန့်သတ်ချက် ရှိပါတယ်။
"""

_VOICE_ALIASES = {
    "male": MALE_VOICE,
    "ကျား": MALE_VOICE,
    "အမျိုးသား": MALE_VOICE,
    MALE_VOICE.lower(): MALE_VOICE,
    "female": FEMALE_VOICE,
    "မ": FEMALE_VOICE,
    "အမျိုးသမီး": FEMALE_VOICE,
    FEMALE_VOICE.lower(): FEMALE_VOICE,
}

_VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi"}


@dataclass(frozen=True, slots=True)
class DubJob:
    job_id: str
    chat_id: int
    user_id: int
    status_message_id: int
    source_kind: Literal["youtube", "telegram"]
    source_value: str
    file_name: str | None
    voice: str


class TelegramDubbingBot:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.pipeline = DubbingPipeline(settings)
        self.application: Application | None = None
        self.queue: asyncio.Queue[DubJob] | None = None
        self.workers: list[asyncio.Task[None]] = []
        self.active_user_ids: set[int] = set()

    async def start(self, application: Application) -> None:
        self.application = application
        self.queue = asyncio.Queue(maxsize=self.settings.max_queue_size)
        self.workers = [
            asyncio.create_task(self._worker(), name=f"dubbing-worker-{index + 1}")
            for index in range(self.settings.workers)
        ]
        await application.bot.set_my_commands(
            [
                BotCommand("start", "Bot ကို စတင်အသုံးပြုရန်"),
                BotCommand("help", "အသုံးပြုနည်း ကြည့်ရန်"),
                BotCommand("voice", "မြန်မာ AI အသံ ရွေးရန်"),
            ]
        )
        logger.info("Started %d dubbing worker(s)", len(self.workers))

    async def stop(self, _application: Application) -> None:
        for worker in self.workers:
            worker.cancel()
        if self.workers:
            await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()

    def register(self, application: Application) -> None:
        private = filters.ChatType.PRIVATE
        application.add_handler(CommandHandler("start", self.start_command, filters=private))
        application.add_handler(CommandHandler("help", self.help_command, filters=private))
        application.add_handler(CommandHandler("voice", self.voice_command, filters=private))
        application.add_handler(
            MessageHandler(private & (filters.VIDEO | filters.Document.ALL), self.video_message)
        )
        application.add_handler(
            MessageHandler(private & filters.TEXT & ~filters.COMMAND, self.text_message)
        )
        application.add_error_handler(self.error_handler)

    @staticmethod
    def _voice(context: ContextTypes.DEFAULT_TYPE, settings: Settings) -> str:
        return str((context.user_data or {}).get("voice", settings.default_voice))

    def _allowed(self, update: Update) -> bool:
        user = update.effective_user
        return bool(user and self.settings.is_user_allowed(user.id))

    async def _deny(self, update: Update) -> None:
        if update.effective_message:
            await update.effective_message.reply_text("ဤ Bot ကို အသုံးပြုခွင့် မပြုထားပါ။")

    async def start_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        del context
        if not self._allowed(update):
            await self._deny(update)
            return
        if update.effective_message:
            await update.effective_message.reply_text(
                _START_TEXT
                + f"\nလက်ရှိ ကြာချိန် ကန့်သတ်ချက်: {self.settings.max_video_seconds} စက္ကန့်"
            )

    async def help_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        await self.start_command(update, context)

    async def voice_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        if not self._allowed(update):
            await self._deny(update)
            return
        message = update.effective_message
        if not message or context.user_data is None:
            return
        if not context.args:
            current = self._voice(context, self.settings)
            label = "အမျိုးသားအသံ" if current == MALE_VOICE else "အမျိုးသမီးအသံ"
            await message.reply_text(
                f"လက်ရှိရွေးထားသည့်အသံ: {label}\n"
                "ပြောင်းရန် /voice male (သို့) /voice female ကို ပို့ပါ။"
            )
            return
        selected = _VOICE_ALIASES.get(" ".join(context.args).lower())
        if not selected:
            await message.reply_text("/voice male (သို့) /voice female ကိုသာ အသုံးပြုပါ။")
            return
        context.user_data["voice"] = selected
        label = "အမျိုးသားအသံ (Thiha)" if selected == MALE_VOICE else "အမျိုးသမီးအသံ (Nilar)"
        await message.reply_text(f"✅ {label} ကို ရွေးချယ်လိုက်ပါပြီ။")

    async def text_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        if not self._allowed(update):
            await self._deny(update)
            return
        message = update.effective_message
        if not message or not message.text:
            return
        url = message.text.strip()
        if not is_supported_youtube_url(url):
            await message.reply_text(
                "YouTube Shorts / watch / live link တစ်ခုလုံးကို ပို့ပါ။\n"
                "ဥပမာ: https://youtube.com/shorts/VIDEO_ID\n"
                "YouTube မဟုတ်သော video ဆိုလျှင် file အနေနဲ့ တင်ပေးနိုင်ပါတယ်။"
            )
            return
        await self._enqueue(update, context, "youtube", url, None)

    async def video_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        if not self._allowed(update):
            await self._deny(update)
            return
        message = update.effective_message
        if not message:
            return
        media = message.video or message.document
        if media is None:
            return
        file_name = getattr(media, "file_name", None)
        mime_type = getattr(media, "mime_type", "") or ""
        suffix = Path(file_name).suffix.lower() if file_name else ""
        if (
            message.document
            and not mime_type.startswith("video/")
            and suffix not in _VIDEO_SUFFIXES
        ):
            await message.reply_text("ဗီဒီယိုဖိုင် (MP4, MOV, MKV, WebM) ကိုသာ ပေးပို့ပါ။")
            return
        file_size = getattr(media, "file_size", None)
        if file_size and file_size > self.settings.max_download_bytes:
            await message.reply_text("ဗီဒီယိုဖိုင်သည် Bot ၏ အရွယ်အစား ကန့်သတ်ချက်ထက် ကြီးနေပါတယ်။")
            return
        await self._enqueue(update, context, "telegram", media.file_id, file_name)

    async def _enqueue(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        source_kind: Literal["youtube", "telegram"],
        source_value: str,
        file_name: str | None,
    ) -> None:
        message = update.effective_message
        user = update.effective_user
        queue = self.queue
        if not message or not user or queue is None:
            return
        if user.id in self.active_user_ids:
            await message.reply_text(
                "သင့်ဗီဒီယိုတစ်ခုကို လုပ်ဆောင်နေဆဲဖြစ်ပါတယ်။ ပြီးဆုံးမှ နောက်တစ်ခု ပို့ပါ။"
            )
            return
        if queue.full():
            await message.reply_text("လက်ရှိ queue ပြည့်နေပါတယ်။ ခဏကြာပြီး ထပ်စမ်းပါ။")
            return

        position = queue.qsize() + 1
        status = await message.reply_text(
            f"⏳ Job ကို လက်ခံရရှိပါတယ်။ Queue အမှတ်စဉ်: {position}\n"
            "ပြီးဆုံးသွားရင် ဒီစာကို အခြေအနေအသစ်နဲ့ ပြောင်းပေးပါမယ်။"
        )
        job = DubJob(
            job_id=uuid.uuid4().hex[:10],
            chat_id=message.chat_id,
            user_id=user.id,
            status_message_id=status.message_id,
            source_kind=source_kind,
            source_value=source_value,
            file_name=file_name,
            voice=self._voice(context, self.settings),
        )
        self.active_user_ids.add(user.id)
        try:
            queue.put_nowait(job)
        except asyncio.QueueFull:
            self.active_user_ids.discard(user.id)
            await status.edit_text("❌ Queue ပြည့်သွားပါတယ်။ ခဏကြာပြီး ထပ်စမ်းပါ။")

    async def _worker(self) -> None:
        while True:
            queue = self.queue
            if queue is None:
                return
            job = await queue.get()
            try:
                await self._process(job)
            except Exception:
                # Keep a malformed job from permanently killing its worker.
                logger.exception("Unhandled worker error for job %s", job.job_id)
            finally:
                self.active_user_ids.discard(job.user_id)
                queue.task_done()

    async def _edit_status(self, job: DubJob, text: str) -> None:
        if not self.application:
            return
        try:
            await self.application.bot.edit_message_text(
                chat_id=job.chat_id,
                message_id=job.status_message_id,
                text=text,
            )
        except TelegramError as exc:
            logger.info("Could not update status for job %s: %s", job.job_id, exc)

    async def _process(self, job: DubJob) -> None:
        if not self.application:
            return
        bot = self.application.bot
        work_dir: Path | None = None

        async def progress(text: str) -> None:
            await self._edit_status(job, text)

        try:
            work_dir = Path(
                tempfile.mkdtemp(prefix=f"{job.job_id}-", dir=self.settings.work_dir)
            )
            if job.source_kind == "youtube":
                await progress("⬇️ YouTube ဗီဒီယိုကို ဒေါင်းလုဒ်လုပ်နေပါတယ်…")
                source = await self.pipeline.download_youtube(job.source_value, work_dir)
            else:
                await progress("⬇️ Telegram ဗီဒီယိုကို ဒေါင်းလုဒ်လုပ်နေပါတယ်…")
                suffix = Path(job.file_name or "").suffix.lower()
                if suffix not in _VIDEO_SUFFIXES:
                    suffix = ".mp4"
                source = work_dir / f"source{suffix}"
                telegram_file = await bot.get_file(
                    job.source_value, read_timeout=60, write_timeout=120
                )
                await telegram_file.download_to_drive(
                    custom_path=source, read_timeout=60, write_timeout=120
                )

            output = await self.pipeline.dub(
                source=source,
                directory=work_dir,
                voice=job.voice,
                progress=progress,
            )
            await progress("📤 မြန်မာအသံပါ ဗီဒီယိုကို Telegram သို့ တင်နေပါတယ်…")
            with output.open("rb") as video_file:
                await bot.send_video(
                    chat_id=job.chat_id,
                    video=video_file,
                    caption="✅ မြန်မာလို အသံအသစ်ထည့်ပြီး ဗီဒီယိုဖြစ်ပါတယ်။",
                    supports_streaming=True,
                    read_timeout=120,
                    write_timeout=180,
                )
            await progress("✅ ပြီးဆုံးပါပြီ။ အောက်ကဗီဒီယိုကို စစ်ကြည့်ပါ။")
        except UserFacingError as exc:
            await progress(f"❌ {exc}")
        except TelegramError:
            logger.exception("Telegram operation failed for job %s", job.job_id)
            await progress("❌ Telegram ချိတ်ဆက်မှုအခက်အခဲကြောင့် Job မပြီးဆုံးနိုင်ပါ။")
        except Exception:
            logger.exception("Dubbing job %s failed", job.job_id)
            await progress(
                "❌ ဗီဒီယိုလုပ်ဆောင်ရာတွင် အခက်အခဲတစ်ခု ဖြစ်ပေါ်ပါတယ်။ "
                "Server log ကို စစ်ဆေးပြီး နောက်မှ ထပ်စမ်းပါ။"
            )
        finally:
            if work_dir:
                await asyncio.to_thread(shutil.rmtree, work_dir, True)

    async def error_handler(
        self, update: object, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        logger.error("Telegram update failed: %s", update, exc_info=context.error)


def create_application(settings: Settings) -> Application:
    service = TelegramDubbingBot(settings)
    application = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .concurrent_updates(False)
        .connect_timeout(30)
        .read_timeout(60)
        .write_timeout(180)
        .post_init(service.start)
        .post_shutdown(service.stop)
        .build()
    )
    service.register(application)
    return application
