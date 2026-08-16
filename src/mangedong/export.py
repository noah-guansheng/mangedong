from __future__ import annotations

from pathlib import Path

import imageio.v2 as imageio
import numpy as np
from PIL import Image


class VideoExporter:
    """Write rendered frames to an MP4 video."""

    def export(self, frame_paths: list[Path], output_path: Path, fps: int) -> Path:
        if not frame_paths:
            raise ValueError("Cannot export a video without frames.")

        output_path = output_path.expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with imageio.get_writer(output_path, fps=fps, codec="libx264", macro_block_size=1) as writer:
            for frame_path in frame_paths:
                with Image.open(frame_path) as frame:
                    writer.append_data(np.asarray(frame.convert("RGB")))

        return output_path
