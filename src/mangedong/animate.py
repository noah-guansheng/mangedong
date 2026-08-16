from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageEnhance


@dataclass(frozen=True)
class KenBurnsAnimator:
    """Generate an anime preview clip from a still page using camera motion."""

    duration_seconds: float = 4.0
    fps: int = 24
    width: int | None = 1280

    def render_frames(self, image: Image.Image, output_dir: Path, stem: str) -> list[Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        source = _fit_width(image.convert("RGB"), self.width)
        frame_count = max(1, int(round(self.duration_seconds * self.fps)))
        frame_paths: list[Path] = []

        for index in range(frame_count):
            progress = 0.0 if frame_count == 1 else index / (frame_count - 1)
            frame = _crop_with_motion(source, progress)
            frame = _apply_cel_pulse(frame, progress)
            frame_path = output_dir / f"{stem}_{index:04d}.png"
            frame.save(frame_path)
            frame_paths.append(frame_path)

        return frame_paths


def _fit_width(image: Image.Image, width: int | None) -> Image.Image:
    if width is None or width <= 0 or image.width == width:
        return _even_size(image)
    height = max(2, round(image.height * (width / image.width)))
    return _even_size(image.resize((width, height), Image.Resampling.LANCZOS))


def _even_size(image: Image.Image) -> Image.Image:
    width = image.width - image.width % 2
    height = image.height - image.height % 2
    if width == image.width and height == image.height:
        return image
    return image.resize((max(2, width), max(2, height)), Image.Resampling.LANCZOS)


def _crop_with_motion(image: Image.Image, progress: float) -> Image.Image:
    eased = 0.5 - math.cos(progress * math.pi) / 2.0
    zoom = 1.0 + 0.18 * eased
    crop_width = int(image.width / zoom)
    crop_height = int(image.height / zoom)

    drift_x = int((image.width - crop_width) * eased)
    drift_y = int((image.height - crop_height) * (1.0 - eased) * 0.7)
    left = min(max(0, drift_x), image.width - crop_width)
    top = min(max(0, drift_y), image.height - crop_height)
    cropped = image.crop((left, top, left + crop_width, top + crop_height))
    return cropped.resize(image.size, Image.Resampling.BICUBIC)


def _apply_cel_pulse(image: Image.Image, progress: float) -> Image.Image:
    brightness = 1.0 + math.sin(progress * math.pi * 2.0) * 0.018
    contrast = 1.0 + math.sin(progress * math.pi) * 0.025
    image = ImageEnhance.Brightness(image).enhance(brightness)
    return ImageEnhance.Contrast(image).enhance(contrast)
