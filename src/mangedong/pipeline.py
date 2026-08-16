from __future__ import annotations

import json
from pathlib import Path

from mangedong.animate import KenBurnsAnimator
from mangedong.colorize import AlgorithmicColorizer
from mangedong.export import VideoExporter
from mangedong.importer import import_pages
from mangedong.models import PipelineConfig, PipelineResult


def run_pipeline(input_path: Path, output_path: Path, config: PipelineConfig) -> PipelineResult:
    """Run the full manga import, colorize, animate, and video export chain."""

    _validate_config(config)
    workdir = config.workdir.expanduser().resolve()
    color_dir = workdir / "colorized"
    frame_dir = workdir / "frames"
    color_dir.mkdir(parents=True, exist_ok=True)
    frame_dir.mkdir(parents=True, exist_ok=True)

    pages = import_pages(input_path)
    colorizer = AlgorithmicColorizer(palette=config.palette)
    animator = KenBurnsAnimator(
        duration_seconds=config.duration_seconds,
        fps=config.fps,
        width=config.width,
    )
    exporter = VideoExporter()

    colorized_paths: list[Path] = []
    frame_paths: list[Path] = []

    for page in pages:
        stem = f"page_{page.page_index:03d}"
        colorized = colorizer.colorize(page.image)
        colorized_path = color_dir / f"{stem}.png"
        colorized.save(colorized_path)
        colorized_paths.append(colorized_path)
        frame_paths.extend(animator.render_frames(colorized, frame_dir, stem))

    exported = exporter.export(frame_paths, output_path, fps=config.fps)
    manifest_path = _write_manifest(
        workdir=workdir,
        input_path=input_path,
        output_path=exported,
        config=config,
        colorized_paths=colorized_paths,
        frame_paths=frame_paths,
    )

    if not config.keep_frames:
        for frame_path in frame_paths:
            frame_path.unlink(missing_ok=True)

    return PipelineResult(
        output_path=exported,
        manifest_path=manifest_path,
        imported_pages=len(pages),
        colorized_pages=tuple(colorized_paths),
        frame_count=len(frame_paths),
    )


def _validate_config(config: PipelineConfig) -> None:
    if config.duration_seconds <= 0:
        raise ValueError("duration_seconds must be greater than 0.")
    if config.fps <= 0:
        raise ValueError("fps must be greater than 0.")
    if config.width is not None and config.width < 2:
        raise ValueError("width must be at least 2 pixels when provided.")


def _write_manifest(
    workdir: Path,
    input_path: Path,
    output_path: Path,
    config: PipelineConfig,
    colorized_paths: list[Path],
    frame_paths: list[Path],
) -> Path:
    manifest = {
        "input": str(input_path.expanduser().resolve()),
        "output": str(output_path),
        "config": {
            "duration_seconds": config.duration_seconds,
            "fps": config.fps,
            "width": config.width,
            "palette": config.palette,
            "keep_frames": config.keep_frames,
        },
        "artifacts": {
            "colorized_pages": [str(path) for path in colorized_paths],
            "frames": [str(path) for path in frame_paths],
        },
        "summary": {
            "imported_pages": len(colorized_paths),
            "frame_count": len(frame_paths),
        },
    }
    manifest_path = workdir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest_path
