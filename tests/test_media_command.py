import asyncio
from pathlib import Path

from myanmar_dubber.media import MediaProcessor
from myanmar_dubber.models import SpeechClip


def test_mux_command_maps_only_video_and_new_dub_audio(tmp_path: Path) -> None:
    processor = MediaProcessor()
    captured: list[str] = []

    async def fake_run(*args: str) -> bytes:
        captured.extend(args)
        return b""

    async def fake_audio_duration(_path: Path) -> float:
        return 2.0

    processor._run = fake_run  # type: ignore[method-assign]
    processor.audio_duration = fake_audio_duration  # type: ignore[method-assign]
    clip = SpeechClip(
        audio_path=tmp_path / "speech.mp3", start=0.5, max_duration=1.0
    )
    asyncio.run(
        processor.mux_dub(
            source=tmp_path / "source.mp4",
            output=tmp_path / "output.mp4",
            clips=[clip],
            duration=3.0,
            video_codec="h264",
        )
    )

    assert captured[captured.index("-c:v") + 1] == "copy"
    assert "0:v:0" in captured
    assert "[dubbed]" in captured
    assert "0:a:0" not in captured
    filters = captured[captured.index("-filter_complex") + 1]
    assert "atempo=2.0" in filters
    assert "adelay=500:all=1" in filters
    assert "normalize=0[dubbed]" in filters
