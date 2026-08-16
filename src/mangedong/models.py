from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image


@dataclass(frozen=True)
class ImportedPage:
    """A manga page loaded from an image, directory, or CBZ archive."""

    source_path: Path
    page_index: int
    image: Image.Image


@dataclass(frozen=True)
class PipelineConfig:
    """Runtime options for the manga-to-anime conversion pipeline."""

    workdir: Path
    duration_seconds: float = 4.0
    fps: int = 24
    width: int | None = 1280
    palette: str = "sunset"
    keep_frames: bool = True


@dataclass(frozen=True)
class PipelineResult:
    """Materialized outputs from one pipeline run."""

    output_path: Path
    manifest_path: Path
    imported_pages: int
    colorized_pages: tuple[Path, ...]
    frame_count: int
