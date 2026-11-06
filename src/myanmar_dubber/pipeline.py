from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Sequence
from pathlib import Path

from openai import AsyncOpenAI

from .config import Settings
from .downloader import YouTubeDownloader
from .errors import UserFacingError
from .media import MediaProcessor
from .models import SpeechClip, TranscriptSegment
from .speech import MyanmarSpeech
from .transcription import Transcriber
from .translation import Translator

logger = logging.getLogger(__name__)
ProgressCallback = Callable[[str], Awaitable[None]]


def speech_slots(
    segments: Sequence[TranscriptSegment], duration: float
) -> list[tuple[float, float]]:
    """Return clip start and maximum duration, using gaps without crossing the next line."""
    slots: list[tuple[float, float]] = []
    for index, segment in enumerate(segments):
        start = min(max(segment.start, 0.0), duration)
        if index + 1 < len(segments):
            slot_end = max(start + 0.2, segments[index + 1].start - 0.05)
        else:
            slot_end = duration
        slot_end = min(max(slot_end, start + 0.05), duration)
        slots.append((start, max(0.05, slot_end - start)))
    return slots


class DubbingPipeline:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.openai = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            timeout=180.0,
            max_retries=2,
        )
        self.transcriber = Transcriber(self.openai, settings.whisper_model)
        self.translator = Translator(self.openai, settings.translation_model)
        self.speech = MyanmarSpeech(settings.tts_rate)
        self.media = MediaProcessor(settings.ffmpeg_timeout_seconds)
        self.youtube = YouTubeDownloader(
            max_duration=settings.max_video_seconds,
            max_bytes=settings.max_download_bytes,
            cookies_file=settings.ytdlp_cookies_file,
        )

    @staticmethod
    async def _report(progress: ProgressCallback | None, message: str) -> None:
        if progress:
            await progress(message)

    async def download_youtube(self, url: str, directory: Path) -> Path:
        return await self.youtube.download(url, directory)

    async def dub(
        self,
        source: Path,
        directory: Path,
        voice: str,
        progress: ProgressCallback | None = None,
    ) -> Path:
        await self._report(progress, "🔎 ဗီဒီယိုကို စစ်ဆေးပြီး မူရင်းအသံကို ခွဲထုတ်နေပါတယ်…")
        info = await self.media.probe_video(source)
        if info.duration > self.settings.max_video_seconds + 0.5:
            raise UserFacingError(
                f"ဗီဒီယိုကြာချိန်ကို {self.settings.max_video_seconds} စက္ကန့်အထိသာ လက်ခံပါတယ်။"
            )
        if source.stat().st_size > self.settings.max_download_bytes:
            raise UserFacingError("ဗီဒီယိုဖိုင်သည် Bot ၏ အရွယ်အစား ကန့်သတ်ချက်ထက် ကြီးနေပါတယ်။")

        extracted_audio = directory / "original_audio.wav"
        await self.media.extract_audio(source, extracted_audio)

        await self._report(progress, "📝 မူရင်းစကားလုံးများကို transcript လုပ်နေပါတယ်…")
        segments = await self.transcriber.transcribe(extracted_audio, info.duration)
        if not segments:
            raise UserFacingError("ဗီဒီယိုထဲတွင် ဘာသာပြန်၍ရသည့် စကားလုံး မတွေ့ရှိပါ။")

        await self._report(
            progress,
            f"🌐 စကားလုံး {len(segments)} ခုကို သဘာဝကျတဲ့ မြန်မာစကားပြေအဖြစ် ဘာသာပြန်နေပါတယ်…",
        )
        translated = await self.translator.translate(segments)

        clips: list[SpeechClip] = []
        slots = speech_slots(segments, info.duration)
        await self._report(progress, "🎙️ မြန်မာ AI အသံအသစ်များ ထုတ်လုပ်နေပါတယ်…")
        update_every = max(1, len(segments) // 5)
        for index, (text, (start, slot)) in enumerate(zip(translated, slots, strict=True)):
            audio_path = directory / f"speech_{index:04d}.mp3"
            await self.speech.synthesize(text, voice, audio_path)
            clips.append(
                SpeechClip(audio_path=audio_path, start=start, max_duration=slot)
            )
            if (index + 1) % update_every == 0 and index + 1 < len(segments):
                await self._report(
                    progress,
                    f"🎙️ မြန်မာ AI အသံ {index + 1}/{len(segments)} ခု ပြီးဆုံးပါပြီ…",
                )

        await self._report(
            progress,
            "🎞️ မူရင်းအသံကို ဖယ်ပြီး မြန်မာအသံအသစ်ကို ဗီဒီယိုထဲ ထည့်နေပါတယ်…",
        )
        output = directory / "myanmar_dub.mp4"
        await self.media.mux_dub(
            source=source,
            output=output,
            clips=clips,
            duration=info.duration,
            video_codec=info.video_codec,
        )

        if output.stat().st_size > self.settings.max_output_bytes:
            await self._report(
                progress, "🗜️ Telegram တင်နိုင်ရန် ဗီဒီယိုအရွယ်အစားကို ချုံ့နေပါတယ်…"
            )
            compressed = directory / "myanmar_dub_compressed.mp4"
            await self.media.compress_for_telegram(
                output, compressed, info.duration, self.settings.max_output_bytes
            )
            output = compressed
        if output.stat().st_size > self.settings.max_output_bytes:
            raise UserFacingError(
                "ပြီးဆုံးသောဗီဒီယိုသည် Telegram upload ကန့်သတ်ချက်ထက် ကြီးနေနေပါတယ်။ "
                "ပိုတိုတဲ့ဗီဒီယိုဖြင့် ထပ်စမ်းပါ။"
            )

        logger.info("Dubbing finished: %d segments, %.1f seconds", len(segments), info.duration)
        return output
