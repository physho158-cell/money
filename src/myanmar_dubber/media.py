from __future__ import annotations

import asyncio
import json
import math
from pathlib import Path

from .errors import MediaError, UserFacingError
from .models import MediaInfo, SpeechClip


def atempo_factors(tempo: float) -> list[float]:
    """Split a tempo into factors supported by ffmpeg's atempo filter."""
    if not math.isfinite(tempo) or tempo <= 0:
        raise ValueError("Tempo must be a positive finite number.")
    factors: list[float] = []
    while tempo > 2.0:
        factors.append(2.0)
        tempo /= 2.0
    while tempo < 0.5:
        factors.append(0.5)
        tempo /= 0.5
    factors.append(round(tempo, 5))
    return factors


class MediaProcessor:
    def __init__(self, timeout_seconds: int = 900) -> None:
        self.timeout_seconds = timeout_seconds

    async def _run(self, *args: str) -> bytes:
        try:
            process = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except OSError as exc:
            raise MediaError(f"Cannot start {args[0]}: {exc}") from exc
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=self.timeout_seconds
            )
        except TimeoutError as exc:
            process.kill()
            await process.communicate()
            raise MediaError(f"{args[0]} timed out.") from exc
        if process.returncode != 0:
            details = stderr.decode("utf-8", errors="replace")[-4000:]
            raise MediaError(f"{args[0]} failed ({process.returncode}): {details}")
        return stdout

    async def _probe_data(self, path: Path) -> dict:
        output = await self._run(
            "ffprobe",
            "-v",
            "error",
            "-show_format",
            "-show_streams",
            "-of",
            "json",
            str(path),
        )
        try:
            return json.loads(output)
        except json.JSONDecodeError as exc:
            raise MediaError("ffprobe returned invalid JSON.") from exc

    @staticmethod
    def _duration(data: dict) -> float:
        try:
            duration = float(data.get("format", {}).get("duration", 0))
        except (TypeError, ValueError) as exc:
            raise MediaError("Media duration is invalid.") from exc
        if not math.isfinite(duration) or duration <= 0:
            raise MediaError("Media duration is missing or invalid.")
        return duration

    async def probe_video(self, path: Path) -> MediaInfo:
        data = await self._probe_data(path)
        video = next(
            (
                stream
                for stream in data.get("streams", [])
                if stream.get("codec_type") == "video"
            ),
            None,
        )
        if video is None:
            raise UserFacingError("ဖိုင်ထဲတွင် ဗီဒီယို stream မတွေ့ရှိပါ။")
        return MediaInfo(
            duration=self._duration(data),
            video_codec=str(video.get("codec_name", "")),
        )

    async def audio_duration(self, path: Path) -> float:
        return self._duration(await self._probe_data(path))

    async def extract_audio(self, source: Path, output: Path) -> None:
        await self._run(
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            str(output),
        )

    async def mux_dub(
        self,
        source: Path,
        output: Path,
        clips: list[SpeechClip],
        duration: float,
        video_codec: str,
    ) -> None:
        if not clips:
            raise ValueError("At least one speech clip is required.")

        command = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
        ]
        for clip in clips:
            command.extend(["-i", str(clip.audio_path)])

        filters = [
            f"anullsrc=r=48000:cl=mono,atrim=duration={duration:.3f}[silence]"
        ]
        speech_labels: list[str] = []
        for index, clip in enumerate(clips):
            clip_duration = await self.audio_duration(clip.audio_path)
            tempo = max(1.0, clip_duration / clip.max_duration)
            tempo_filters = ",".join(f"atempo={factor}" for factor in atempo_factors(tempo))
            if tempo_filters:
                tempo_filters += ","
            delay_ms = max(0, round(clip.start * 1000))
            label = f"speech{index}"
            filters.append(
                f"[{index + 1}:a]aresample=48000,"
                f"aformat=channel_layouts=mono,{tempo_filters}apad,"
                f"atrim=duration={clip.max_duration:.3f},"
                f"adelay={delay_ms}:all=1,asetpts=N/SR/TB[{label}]"
            )
            speech_labels.append(f"[{label}]")

        mix_inputs = "".join(["[silence]", *speech_labels])
        filters.append(
            f"{mix_inputs}amix=inputs={len(clips) + 1}:duration=first:"
            "dropout_transition=0:normalize=0[dubbed]"
        )
        command.extend(["-filter_complex", ";".join(filters)])
        command.extend(["-map", "0:v:0", "-map", "[dubbed]", "-sn", "-dn"])
        if video_codec == "h264":
            command.extend(["-c:v", "copy"])
        else:
            command.extend(
                [
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-crf",
                    "23",
                    "-pix_fmt",
                    "yuv420p",
                ]
            )
        command.extend(
            [
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                "-ac",
                "1",
                "-map_metadata",
                "-1",
                "-movflags",
                "+faststart",
                "-t",
                f"{duration:.3f}",
                str(output),
            ]
        )
        await self._run(*command)

    async def compress_for_telegram(
        self, source: Path, output: Path, duration: float, max_bytes: int
    ) -> None:
        audio_bitrate = 96_000
        target_total = int(max_bytes * 8 * 0.88 / duration)
        video_bitrate = max(150_000, target_total - audio_bitrate)
        await self._run(
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(source),
            "-map",
            "0:v:0",
            "-map",
            "0:a:0",
            "-vf",
            "scale=w='min(iw,1280)':h='min(ih,1280)':"
            "force_original_aspect_ratio=decrease:force_divisible_by=2",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-b:v",
            str(video_bitrate),
            "-maxrate",
            str(video_bitrate),
            "-bufsize",
            str(video_bitrate * 2),
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            str(audio_bitrate),
            "-movflags",
            "+faststart",
            "-t",
            f"{duration:.3f}",
            str(output),
        )
