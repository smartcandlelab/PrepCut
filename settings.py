# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


AUDIO_AAC = "aac"
AUDIO_PCM_16 = "pcm16"

UNSUPPORTED_FAIL = "fail"
UNSUPPORTED_PRORES_LT = "prores_lt"
UNSUPPORTED_PRORES_422 = "prores_422"

APP_NAME = "PrepCut"


@dataclass
class PrepCutSettings:
    output_dir: Path
    audio_mode: str = AUDIO_AAC
    unsupported_video_mode: str = UNSUPPORTED_FAIL
    emergency_mode: bool = False


def default_output_dir() -> Path:
    return Path.home() / "Movies" / APP_NAME


def settings_path() -> Path:
    return Path.home() / "Library" / "Application Support" / APP_NAME / "settings.json"


def load_settings() -> PrepCutSettings:
    defaults = PrepCutSettings(output_dir=default_output_dir())
    path = settings_path()

    if not path.exists():
        defaults.output_dir.mkdir(parents=True, exist_ok=True)
        save_settings(defaults)
        return defaults

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        defaults.output_dir.mkdir(parents=True, exist_ok=True)
        return defaults

    settings = PrepCutSettings(
        output_dir=Path(raw.get("output_dir") or defaults.output_dir).expanduser(),
        audio_mode=_valid_choice(raw.get("audio_mode"), {AUDIO_AAC, AUDIO_PCM_16}, AUDIO_AAC),
        unsupported_video_mode=_valid_choice(
            raw.get("unsupported_video_mode"),
            {UNSUPPORTED_FAIL, UNSUPPORTED_PRORES_LT, UNSUPPORTED_PRORES_422},
            UNSUPPORTED_FAIL,
        ),
        emergency_mode=bool(raw.get("emergency_mode", False)),
    )
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    return settings


def save_settings(settings: PrepCutSettings) -> None:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    data: dict[str, Any] = asdict(settings)
    data["output_dir"] = str(settings.output_dir)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def reset_processing_defaults(settings: PrepCutSettings) -> PrepCutSettings:
    settings.audio_mode = AUDIO_AAC
    settings.unsupported_video_mode = UNSUPPORTED_FAIL
    settings.emergency_mode = False
    return settings


def reset_output_folder(settings: PrepCutSettings) -> PrepCutSettings:
    settings.output_dir = default_output_dir()
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    return settings


def display_path(path: Path) -> str:
    home = Path.home()
    try:
        relative = path.resolve().relative_to(home.resolve())
    except ValueError:
        return str(path)
    return str(Path("~") / relative)


def _valid_choice(value: object, valid: set[str], fallback: str) -> str:
    if isinstance(value, str) and value in valid:
        return value
    return fallback
