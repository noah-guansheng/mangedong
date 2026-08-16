from __future__ import annotations

import json
from pathlib import Path
from zipfile import ZipFile

from PIL import Image, ImageChops, ImageDraw

from mangedong.importer import import_pages
from mangedong.models import PipelineConfig
from mangedong.pipeline import run_pipeline


def test_pipeline_exports_mp4_and_manifest(tmp_path: Path) -> None:
    source = tmp_path / "page.png"
    _draw_manga_page(source)

    result = run_pipeline(
        input_path=source,
        output_path=tmp_path / "out.mp4",
        config=PipelineConfig(
            workdir=tmp_path / "work",
            duration_seconds=0.5,
            fps=4,
            width=320,
            palette="cel",
        ),
    )

    assert result.imported_pages == 1
    assert result.frame_count == 2
    assert result.output_path.exists()
    assert result.output_path.stat().st_size > 1_000
    assert result.colorized_pages[0].exists()
    assert result.manifest_path.exists()

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["summary"] == {"imported_pages": 1, "frame_count": 2}
    assert manifest["config"]["palette"] == "cel"
    assert Path(manifest["output"]).name == "out.mp4"
    first_frame = Image.open(manifest["artifacts"]["frames"][0])
    last_frame = Image.open(manifest["artifacts"]["frames"][-1])
    assert ImageChops.difference(first_frame, last_frame).getbbox() is not None


def test_directory_import_sorts_supported_images(tmp_path: Path) -> None:
    _draw_manga_page(tmp_path / "002.png")
    _draw_manga_page(tmp_path / "001.jpg")
    (tmp_path / "notes.txt").write_text("not a page", encoding="utf-8")

    pages = import_pages(tmp_path)

    assert [page.source_path.name for page in pages] == ["001.jpg", "002.png"]
    assert [page.page_index for page in pages] == [0, 1]


def test_cbz_import_reads_pages_in_archive_order(tmp_path: Path) -> None:
    first = tmp_path / "001.png"
    second = tmp_path / "002.png"
    _draw_manga_page(first)
    _draw_manga_page(second)
    archive = tmp_path / "chapter.cbz"
    with ZipFile(archive, "w") as cbz:
        cbz.write(second, arcname="pages/002.png")
        cbz.write(first, arcname="pages/001.png")

    pages = import_pages(archive)

    assert [page.source_path.as_posix() for page in pages] == ["pages/001.png", "pages/002.png"]
    assert all(page.image.mode == "RGB" for page in pages)


def _draw_manga_page(path: Path) -> None:
    image = Image.new("L", (240, 320), 245)
    draw = ImageDraw.Draw(image)
    draw.rectangle((15, 15, 225, 150), outline=15, width=4)
    draw.rectangle((15, 170, 225, 305), outline=15, width=4)
    draw.ellipse((70, 35, 170, 135), outline=20, width=5)
    draw.arc((80, 55, 160, 130), 10, 170, fill=20, width=3)
    draw.polygon([(35, 190), (120, 180), (205, 280), (60, 290)], outline=30, fill=235)
    draw.line((35, 260, 205, 210), fill=25, width=4)
    image.save(path)
