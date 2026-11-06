from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class TranscriptSegment:
    start: float
    end: float
    text: str


@dataclass(frozen=True, slots=True)
class SpeechClip:
    audio_path: Path
    start: float
    max_duration: float


@dataclass(frozen=True, slots=True)
class MediaInfo:
    duration: float
    video_codec: str
