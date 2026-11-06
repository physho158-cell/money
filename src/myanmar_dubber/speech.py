from __future__ import annotations

import asyncio
from pathlib import Path

import edge_tts

from .errors import UserFacingError


class MyanmarSpeech:
    def __init__(self, rate: str = "+0%") -> None:
        self.rate = rate

    async def synthesize(self, text: str, voice: str, output_path: Path) -> None:
        last_error: Exception | None = None
        for attempt in range(3):
            try:
                communicate = edge_tts.Communicate(text=text, voice=voice, rate=self.rate)
                await communicate.save(str(output_path))
                if output_path.stat().st_size < 100:
                    raise RuntimeError("The TTS service returned an empty audio file.")
                return
            except Exception as exc:  # edge-tts exposes several transport exception types
                last_error = exc
                output_path.unlink(missing_ok=True)
                if attempt < 2:
                    await asyncio.sleep(1.5 * (attempt + 1))
        raise UserFacingError(
            "မြန်မာ AI အသံထုတ်ရာတွင် ချိတ်ဆက်မှု အခက်အခဲရှိနေပါတယ်။ ခဏကြာပြီး ထပ်စမ်းပါ။"
        ) from last_error
