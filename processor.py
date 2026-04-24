from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from settings import (
    AUDIO_AAC,
    AUDIO_PCM_16,
    UNSUPPORTED_FAIL,
    UNSUPPORTED_PRORES_422,
    UNSUPPORTED_PRORES_LT,
    PrepCutSettings,
)


SUPPORTED_VIDEO_CODECS = {"prores", "h264", "hevc"}
SUPPORTED_AUDIO_CODECS = {
    "aac",
    "pcm_s16le",
    "pcm_s24le",
    "pcm_s32le",
    "pcm_f32le",
    "pcm_f64le",
}
MIN_AAC_BITRATE = 192_000


class ProcessingError(Exception):
    """Base error shown in the queue status."""


class UnsupportedVideoError(ProcessingError):
    """Raised when the video stream would require video re-encoding."""


@dataclass(frozen=True)
class ProbeInfo:
    container: str | None
    video_codec: str | None
    audio_codec: str | None
    audio_bitrate: int | None = None


@dataclass(frozen=True)
class ProcessResult:
    output_path: Path
    probe_info: ProbeInfo


def find_tool(name: str) -> Path | None:
    for candidate in _bundle_tool_candidates(name):
        if _is_executable(candidate):
            return candidate

    dev_candidate = Path(__file__).resolve().parent / "vendor" / "ffmpeg" / name
    if _is_executable(dev_candidate):
        return dev_candidate

    path_candidate = shutil.which(name)
    if path_candidate:
        return Path(path_candidate)

    return None


def require_tool(name: str) -> Path:
    tool = find_tool(name)
    if tool:
        return tool
    raise ProcessingError(
        f"{name} not found. Place ffmpeg and ffprobe in ./vendor/ffmpeg/ "
        "or install them on PATH."
    )


def inspect_file(input_path: Path) -> ProbeInfo:
    if not input_path.is_file():
        raise ProcessingError("File cannot be read.")

    ffprobe = require_tool("ffprobe")
    command = [
        str(ffprobe),
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(input_path),
    ]

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise ProcessingError("ffprobe not found next to PrepCut.") from exc
    except OSError as exc:
        raise ProcessingError("ffprobe cannot be run.") from exc

    if completed.returncode != 0:
        raise ProcessingError("File cannot be read.")

    try:
        data = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ProcessingError("File cannot be read.") from exc

    streams = data.get("streams", [])
    video_stream = _first_stream(streams, "video")
    audio_stream = _first_stream(streams, "audio")
    video_codec = _codec_name(video_stream)
    audio_codec = _codec_name(audio_stream)
    container = data.get("format", {}).get("format_name")

    if not video_codec:
        raise ProcessingError("No video stream found.")

    return ProbeInfo(
        container=container,
        video_codec=normalize_video_codec(video_codec),
        audio_codec=normalize_audio_codec(audio_codec) if audio_codec else None,
        audio_bitrate=_audio_bitrate(audio_stream),
    )


def process_file(
    input_path: Path,
    output_dir: Path,
    settings: PrepCutSettings,
) -> ProcessResult:
    probe_info = inspect_file(input_path)

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = unique_output_path(output_dir, input_path)
    command = build_ffmpeg_command(input_path, output_path, probe_info, settings)
    run_ffmpeg(command)

    return ProcessResult(output_path=output_path, probe_info=probe_info)


def build_ffmpeg_command(
    input_path: Path,
    output_path: Path,
    probe_info: ProbeInfo,
    settings: PrepCutSettings,
) -> list[str]:
    ffmpeg = require_tool("ffmpeg")

    if settings.emergency_mode:
        return [
            str(ffmpeg),
            "-i",
            str(input_path),
            "-c:v",
            "prores_videotoolbox",
            "-profile:v",
            "2",
            "-c:a",
            "pcm_s16le",
            str(output_path),
        ]

    if is_video_compatible(probe_info.video_codec):
        if is_audio_compatible(probe_info.audio_codec):
            return [
                str(ffmpeg),
                "-i",
                str(input_path),
                "-c",
                "copy",
                str(output_path),
            ]

        return [
            str(ffmpeg),
            "-i",
            str(input_path),
            "-c:v",
            "copy",
            *audio_conversion_args(settings, probe_info),
            str(output_path),
        ]

    if settings.unsupported_video_mode == UNSUPPORTED_FAIL:
        raise UnsupportedVideoError(
            "Video codec unsupported by Final Cut. To convert, open Settings."
        )

    if settings.unsupported_video_mode == UNSUPPORTED_PRORES_LT:
        profile = "1"
    elif settings.unsupported_video_mode == UNSUPPORTED_PRORES_422:
        profile = "2"
    else:
        raise ProcessingError("Invalid unsupported video setting.")

    audio_args = (
        ["-c:a", "copy"]
        if is_audio_compatible(probe_info.audio_codec)
        else audio_conversion_args(settings, probe_info)
    )
    return [
        str(ffmpeg),
        "-i",
        str(input_path),
        "-c:v",
        "prores_videotoolbox",
        "-profile:v",
        profile,
        *audio_args,
        str(output_path),
    ]


def audio_conversion_args(
    settings: PrepCutSettings,
    probe_info: ProbeInfo,
) -> list[str]:
    if settings.audio_mode == AUDIO_PCM_16:
        return ["-c:a", "pcm_s16le"]

    if settings.audio_mode == AUDIO_AAC:
        return [
            "-c:a",
            "aac",
            "-b:a",
            aac_bitrate_arg(probe_info.audio_bitrate),
        ]

    raise ProcessingError("Invalid audio setting.")


def run_ffmpeg(command: list[str]) -> None:
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError as exc:
        raise ProcessingError("ffmpeg not found next to PrepCut.") from exc
    except OSError as exc:
        raise ProcessingError("ffmpeg cannot be run.") from exc

    if completed.returncode != 0:
        raise ProcessingError("ffmpeg failed.")


def is_audio_compatible(audio_codec: str | None) -> bool:
    if audio_codec is None:
        return True
    return normalize_audio_codec(audio_codec) in SUPPORTED_AUDIO_CODECS


def is_video_compatible(video_codec: str | None) -> bool:
    if video_codec is None:
        return False
    return normalize_video_codec(video_codec) in SUPPORTED_VIDEO_CODECS


def aac_bitrate_arg(audio_bitrate: int | None) -> str:
    if audio_bitrate and audio_bitrate > MIN_AAC_BITRATE:
        return str(audio_bitrate)
    return "192k"


def unique_output_path(output_dir: Path, input_path: Path) -> Path:
    base_name = f"{input_path.stem} - PrepCut"
    candidate = output_dir / f"{base_name}.mov"
    index = 1

    while candidate.exists():
        candidate = output_dir / f"{base_name}_{index}.mov"
        index += 1

    return candidate


def normalize_video_codec(codec: str) -> str:
    codec = codec.lower()
    if codec in {"h265", "x265"}:
        return "hevc"
    if codec in {"avc", "avc1", "x264"}:
        return "h264"
    return codec


def normalize_audio_codec(codec: str) -> str:
    return codec.lower()


def _bundle_tool_candidates(name: str) -> list[Path]:
    candidates: list[Path] = []
    executable_path = Path(sys.executable).resolve()

    if getattr(sys, "frozen", False):
        candidates.extend(
            [
                executable_path.parent / name,
                executable_path.parent.parent / "Resources" / "vendor" / "ffmpeg" / name,
            ]
        )
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(Path(meipass) / "vendor" / "ffmpeg" / name)

    return candidates


def _is_executable(path: Path) -> bool:
    return path.is_file() and path.stat().st_mode & 0o111 != 0


def _first_stream(streams: list[dict], codec_type: str) -> dict | None:
    for stream in streams:
        if stream.get("codec_type") == codec_type:
            return stream
    return None


def _codec_name(stream: dict | None) -> str | None:
    if not stream:
        return None
    codec = stream.get("codec_name")
    return codec if isinstance(codec, str) else None


def _audio_bitrate(stream: dict | None) -> int | None:
    if not stream:
        return None
    bit_rate = stream.get("bit_rate")
    if not bit_rate:
        return None
    try:
        return int(bit_rate)
    except (TypeError, ValueError):
        return None
