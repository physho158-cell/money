import asyncio
from pathlib import Path

from myanmar_dubber.media import MediaProcessor
from myanmar_dubber.models import SpeechClip


def test_enhance_reencodes_with_lightweight_filters(tmp_path: Path) -> None:
    processor = MediaProcessor()
    captured: list[str] = []

    async def fake_run(*args: str) -> bytes:
        captured.extend(args)
        return b""

    async def fake_audio_duration(_path: Path) -> float:
        return 1.0

    processor._run = fake_run  # type: ignore[method-assign]
    processor.audio_duration = fake_audio_duration  # type: ignore[method-assign]
    clip = SpeechClip(audio_path=tmp_path / "speech.mp3", start=0, max_duration=1)
    asyncio.run(
        processor.mux_dub(
            source=tmp_path / "source.mp4",
            output=tmp_path / "output.mp4",
            clips=[clip],
            duration=2.0,
            video_codec="h264",
            enhance=True,
        )
    )
    filters = captured[captured.index("-vf") + 1]
    assert "hqdn3d" in filters
    assert "unsharp" in filters
    assert "eq=contrast" in filters
    assert captured[captured.index("-c:v") + 1] == "libx264"
    assert captured[captured.index("-crf") + 1] == "19"
