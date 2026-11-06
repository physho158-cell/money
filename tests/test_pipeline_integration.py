import asyncio
from pathlib import Path

import pytest

from myanmar_dubber.config import Settings
from myanmar_dubber.errors import UserFacingError
from myanmar_dubber.models import MediaInfo, TranscriptSegment
from myanmar_dubber.pipeline import DubbingPipeline


class FakeMedia:
    def __init__(self) -> None:
        self.clips = []

    async def probe_video(self, _source: Path) -> MediaInfo:
        return MediaInfo(duration=6.0, video_codec="h264")

    async def extract_audio(self, _source: Path, output: Path) -> None:
        output.write_bytes(b"audio")

    async def mux_dub(self, **kwargs) -> None:
        self.clips = kwargs["clips"]
        kwargs["output"].write_bytes(b"dubbed video")


class FakeTranscriber:
    def __init__(self, with_speech: bool = True) -> None:
        self.with_speech = with_speech

    async def transcribe(self, _audio: Path, _duration: float) -> list[TranscriptSegment]:
        if not self.with_speech:
            return []
        return [
            TranscriptSegment(start=0.0, end=1.5, text="Hello"),
            TranscriptSegment(start=2.0, end=3.0, text="How are you?"),
        ]


class FakeTranslator:
    async def translate(self, segments: list[TranscriptSegment]) -> list[str]:
        assert len(segments) == 2
        return ["မင်္ဂလာပါ", "နေကောင်းလား"]


class FakeSpeech:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def synthesize(self, text: str, voice: str, output: Path) -> None:
        self.calls.append((text, voice))
        output.write_bytes(b"speech" * 20)


def _pipeline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> DubbingPipeline:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "telegram-test-token")
    monkeypatch.setenv("GROQ_API_KEY", "groq-test-token")
    settings = Settings.from_env()
    pipeline = DubbingPipeline(settings)
    pipeline.media = FakeMedia()  # type: ignore[assignment]
    pipeline.transcriber = FakeTranscriber()  # type: ignore[assignment]
    pipeline.translator = FakeTranslator()  # type: ignore[assignment]
    pipeline.speech = FakeSpeech()  # type: ignore[assignment]
    return pipeline


def test_dub_orchestrates_all_stages(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pipeline = _pipeline(tmp_path, monkeypatch)
    source = tmp_path / "source.mp4"
    source.write_bytes(b"source")
    progress: list[str] = []

    async def report(message: str) -> None:
        progress.append(message)

    output = asyncio.run(
        pipeline.dub(source, tmp_path, "my-MM-ThihaNeural", report)
    )

    assert output.read_bytes() == b"dubbed video"
    assert pipeline.speech.calls == [  # type: ignore[attr-defined]
        ("မင်္ဂလာပါ", "my-MM-ThihaNeural"),
        ("နေကောင်းလား", "my-MM-ThihaNeural"),
    ]
    assert len(pipeline.media.clips) == 2  # type: ignore[attr-defined]
    assert any("transcript" in message for message in progress)
    assert any("ဘာသာပြန်" in message for message in progress)


def test_dub_rejects_video_without_speech(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pipeline = _pipeline(tmp_path, monkeypatch)
    pipeline.transcriber = FakeTranscriber(with_speech=False)  # type: ignore[assignment]
    source = tmp_path / "source.mp4"
    source.write_bytes(b"source")
    with pytest.raises(UserFacingError, match="စကားလုံး"):
        asyncio.run(pipeline.dub(source, tmp_path, "my-MM-NilarNeural"))
