from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Annotated

import typer

from mangedong.colorize import PALETTES
from mangedong.importer import IMAGE_EXTENSIONS
from mangedong.models import PipelineConfig
from mangedong.pipeline import run_pipeline


app = typer.Typer(
    help="Convert black-and-white manga pages into simple anime-style MP4 clips.",
    no_args_is_help=True,
)


@app.command()
def run(
    input_path: Annotated[
        Path,
        typer.Option("--input", "-i", exists=True, readable=True, help="Image, image directory, or CBZ/ZIP archive."),
    ],
    output_path: Annotated[Path, typer.Option("--output", "-o", help="Destination MP4 path.")] = Path("output.mp4"),
    workdir: Annotated[Path, typer.Option("--workdir", "-w", help="Directory for intermediate artifacts.")] = Path(
        "runs/latest"
    ),
    duration: Annotated[float, typer.Option("--duration", min=0.1, help="Seconds of video per imported page.")] = 4.0,
    fps: Annotated[int, typer.Option("--fps", min=1, max=60, help="Frames per second.")] = 24,
    width: Annotated[int | None, typer.Option("--width", help="Output width in pixels.")] = 1280,
    palette: Annotated[
        str,
        typer.Option("--palette", help=f"Color palette: {', '.join(sorted(PALETTES))}."),
    ] = "sunset",
    keep_frames: Annotated[bool, typer.Option("--keep-frames/--no-keep-frames", help="Keep rendered PNG frames.")] = True,
) -> None:
    """Run one end-to-end manga-to-anime conversion."""

    result = run_pipeline(
        input_path=input_path,
        output_path=output_path,
        config=PipelineConfig(
            workdir=workdir,
            duration_seconds=duration,
            fps=fps,
            width=width,
            palette=palette,
            keep_frames=keep_frames,
        ),
    )

    typer.echo(f"Imported pages: {result.imported_pages}")
    typer.echo(f"Rendered frames: {result.frame_count}")
    typer.echo(f"Video: {result.output_path}")
    typer.echo(f"Manifest: {result.manifest_path}")


@app.command()
def batch(
    input_dir: Annotated[Path, typer.Argument(exists=True, file_okay=False, readable=True, help="Directory of manga pages.")],
    output_dir: Annotated[Path, typer.Argument(help="Directory where MP4 clips will be written.")],
    workdir: Annotated[Path, typer.Option("--workdir", "-w", help="Directory for intermediate artifacts.")] = Path(
        "runs/batch"
    ),
    duration: Annotated[float, typer.Option("--duration", min=0.1, help="Seconds of video per source image.")] = 4.0,
    fps: Annotated[int, typer.Option("--fps", min=1, max=60, help="Frames per second.")] = 24,
    width: Annotated[int | None, typer.Option("--width", help="Output width in pixels.")] = 1280,
    palette: Annotated[str, typer.Option("--palette", help=f"Color palette: {', '.join(sorted(PALETTES))}.")] = "sunset",
) -> None:
    """Convert every supported image in a directory into its own MP4 clip."""

    sources = sorted(path for path in input_dir.iterdir() if path.suffix.lower() in IMAGE_EXTENSIONS)
    if not sources:
        raise typer.BadParameter(f"No supported images found in {input_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    for source in sources:
        result = run_pipeline(
            input_path=source,
            output_path=output_dir / f"{source.stem}.mp4",
            config=PipelineConfig(
                workdir=workdir / source.stem,
                duration_seconds=duration,
                fps=fps,
                width=width,
                palette=palette,
                keep_frames=True,
            ),
        )
        typer.echo(f"{source.name} -> {result.output_path}")


@app.command()
def doctor() -> None:
    """Check whether local runtime dependencies needed by the MVP are importable."""

    checks = {
        "Pillow": importlib.util.find_spec("PIL") is not None,
        "NumPy": importlib.util.find_spec("numpy") is not None,
        "ImageIO": importlib.util.find_spec("imageio") is not None,
        "ImageIO FFmpeg": importlib.util.find_spec("imageio_ffmpeg") is not None,
    }
    for name, available in checks.items():
        typer.echo(f"{name}: {'ok' if available else 'missing'}")

    if not all(checks.values()):
        raise typer.Exit(code=1)


@app.command("serve")
def serve_cmd(
    host: Annotated[str, typer.Option("--host", help="Bind host.")] = "0.0.0.0",
    port: Annotated[int, typer.Option("--port", min=1, max=65535, help="Bind port.")] = 8000,
) -> None:
    """Start the studio workbench (same as ./start.sh after install)."""

    import os

    import uvicorn

    os.environ.setdefault("MANGEDONG_DATABASE_URL", "sqlite:///./mangedong.db")
    os.environ.setdefault("MANGEDONG_STORAGE_DIR", "./mangedong_storage")
    typer.echo(f"mangedong 工作台: http://127.0.0.1:{port}/app")
    uvicorn.run("mangedong.api.app:create_app", factory=True, host=host, port=port)


@app.command("worker")
def worker_cmd(
    database_url: Annotated[str | None, typer.Option("--database-url", help="Shared database URL for the job queue.")] = None,
    storage_dir: Annotated[Path | None, typer.Option("--storage-dir", help="Local cache directory.")] = None,
    interval: Annotated[float, typer.Option("--interval", min=0.2, help="Polling interval in seconds.")] = 1.0,
) -> None:
    """Run a multi-machine worker that claims jobs from the shared database queue."""

    from mangedong.api.db import build_session_factory, init_db
    from mangedong.api.worker import run_worker_forever, worker_id
    import os
    import threading

    resolved_db = database_url or os.getenv("MANGEDONG_DATABASE_URL", "sqlite:///./mangedong.db")
    resolved_storage = Path(storage_dir or os.getenv("MANGEDONG_STORAGE_DIR", "./mangedong_storage")).resolve()
    resolved_storage.mkdir(parents=True, exist_ok=True)
    session_factory = build_session_factory(resolved_db)
    init_db(session_factory)
    stop = threading.Event()
    typer.echo(f"worker {worker_id()} queue=database db={resolved_db}")
    try:
        run_worker_forever(session_factory, resolved_storage, stop, interval=interval)
    except KeyboardInterrupt:
        stop.set()


if __name__ == "__main__":
    app()
