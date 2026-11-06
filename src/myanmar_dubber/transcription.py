from __future__ import annotations

import math
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI

from .models import TranscriptSegment


def _field(value: object, name: str) -> Any:
    if isinstance(value, dict):
        return value.get(name)
    return getattr(value, name, None)


def _number(value: object) -> float | None:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def normalise_segments(
    raw_segments: Iterable[object] | None, duration: float
) -> list[TranscriptSegment]:
    """Convert SDK/model dictionaries into safe, sorted transcript segments."""
    segments: list[TranscriptSegment] = []
    for raw in raw_segments or []:
        text = str(_field(raw, "text") or "").strip()
        start = _number(_field(raw, "start"))
        end = _number(_field(raw, "end"))
        if not text or start is None or end is None:
            continue
        start = min(max(start, 0.0), duration)
        end = min(max(end, 0.0), duration)
        if end <= start:
            continue
        segments.append(TranscriptSegment(start=start, end=end, text=text))
    segments.sort(key=lambda segment: segment.start)
    return segments


class Transcriber:
    def __init__(self, client: AsyncOpenAI, model: str) -> None:
        self.client = client
        self.model = model

    async def transcribe(self, audio_path: Path, duration: float) -> list[TranscriptSegment]:
        with audio_path.open("rb") as audio_file:
            response = await self.client.audio.transcriptions.create(
                model=self.model,
                file=audio_file,
                response_format="verbose_json",
                timestamp_granularities=["segment"],
            )
        segments = normalise_segments(_field(response, "segments"), duration)
        if segments:
            return segments

        # Some compatible Whisper endpoints omit timestamps. Keep a useful fallback.
        full_text = str(_field(response, "text") or "").strip()
        if full_text:
            return [TranscriptSegment(start=0.0, end=duration, text=full_text)]
        return []
