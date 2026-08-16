from __future__ import annotations

import json
import math
import re
import wave
from pathlib import Path
from zipfile import ZipFile


def safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", name).strip(".-")
    return cleaned or "asset"


def project_storage(root: Path, project_id: int, *parts: str) -> Path:
    path = root / "projects" / str(project_id)
    for part in parts:
        path = path / safe_filename(part)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def write_mock_wav(path: Path, duration_seconds: float = 1.2, frequency: float = 440.0) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    sample_rate = 48_000
    frame_count = int(sample_rate * duration_seconds)
    with wave.open(str(path), "w") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        for index in range(frame_count):
            value = int(math.sin(2 * math.pi * frequency * index / sample_rate) * 12_000)
            wav.writeframesraw(value.to_bytes(2, byteorder="little", signed=True))
    return path


def write_srt(path: Path, text: str, start: float = 0.0, end: float = 2.0) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "1\n{start} --> {end}\n{text}\n".format(
            start=_srt_time(start),
            end=_srt_time(end),
            text=text,
        ),
        encoding="utf-8",
    )
    return path


def write_export_package(path: Path, manifest: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(path, "w") as archive:
        archive.writestr("manifest/manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        archive.writestr("readme.txt", "mangedong commercial delivery package\n")
    return path


def _srt_time(seconds: float) -> str:
    milliseconds = int(seconds * 1000)
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
