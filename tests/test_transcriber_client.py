import asyncio
from pathlib import Path
from types import SimpleNamespace

from myanmar_dubber.transcription import Transcriber


class FakeTranscriptions:
    def __init__(self, response: object) -> None:
        self.response = response
        self.kwargs = {}

    async def create(self, **kwargs: object) -> object:
        self.kwargs = kwargs
        return self.response


def test_transcriber_uses_segment_timestamps(tmp_path: Path) -> None:
    response = SimpleNamespace(
        segments=[{"start": 0, "end": 1.25, "text": "Hello"}], text="Hello"
    )
    endpoint = FakeTranscriptions(response)
    client = SimpleNamespace(audio=SimpleNamespace(transcriptions=endpoint))
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"audio")
    segments = asyncio.run(Transcriber(client, "whisper-1").transcribe(audio, 4.0))  # type: ignore[arg-type]
    assert len(segments) == 1
    assert segments[0].end == 1.25
    assert endpoint.kwargs["timestamp_granularities"] == ["segment"]


def test_transcriber_falls_back_to_full_text(tmp_path: Path) -> None:
    endpoint = FakeTranscriptions(SimpleNamespace(segments=[], text="Full text"))
    client = SimpleNamespace(audio=SimpleNamespace(transcriptions=endpoint))
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"audio")
    segments = asyncio.run(Transcriber(client, "whisper-1").transcribe(audio, 4.0))  # type: ignore[arg-type]
    assert len(segments) == 1
    assert segments[0].start == 0
    assert segments[0].end == 4.0
    assert segments[0].text == "Full text"
