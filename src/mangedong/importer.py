from __future__ import annotations

from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

from PIL import Image, ImageOps

from mangedong.models import ImportedPage


IMAGE_EXTENSIONS = {".bmp", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}
ARCHIVE_EXTENSIONS = {".cbz", ".zip"}


def import_pages(input_path: Path) -> list[ImportedPage]:
    """Load manga pages from an image file, a directory of images, or a CBZ/ZIP archive."""

    input_path = input_path.expanduser().resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Input path does not exist: {input_path}")

    if input_path.is_dir():
        page_paths = sorted(path for path in input_path.iterdir() if path.suffix.lower() in IMAGE_EXTENSIONS)
        if not page_paths:
            raise ValueError(f"No supported image pages found in directory: {input_path}")
        return [_page_from_file(path, index) for index, path in enumerate(page_paths)]

    suffix = input_path.suffix.lower()
    if suffix in IMAGE_EXTENSIONS:
        return [_page_from_file(input_path, 0)]
    if suffix in ARCHIVE_EXTENSIONS:
        return _pages_from_archive(input_path)

    supported = ", ".join(sorted(IMAGE_EXTENSIONS | ARCHIVE_EXTENSIONS))
    raise ValueError(f"Unsupported input type '{suffix}'. Supported extensions: {supported}")


def _page_from_file(path: Path, page_index: int) -> ImportedPage:
    image = Image.open(path)
    return ImportedPage(source_path=path, page_index=page_index, image=_normalize_image(image))


def _pages_from_archive(path: Path) -> list[ImportedPage]:
    pages: list[ImportedPage] = []
    with ZipFile(path) as archive:
        names = sorted(
            name
            for name in archive.namelist()
            if not name.endswith("/") and Path(name).suffix.lower() in IMAGE_EXTENSIONS
        )
        if not names:
            raise ValueError(f"No supported image pages found in archive: {path}")

        for index, name in enumerate(names):
            with archive.open(name) as member:
                image = Image.open(BytesIO(member.read()))
                pages.append(ImportedPage(source_path=Path(name), page_index=index, image=_normalize_image(image)))

    return pages


def _normalize_image(image: Image.Image) -> Image.Image:
    return ImageOps.exif_transpose(image).convert("RGB")
