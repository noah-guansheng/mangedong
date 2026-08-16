from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageFilter


PALETTES: dict[str, tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]] = {
    "sunset": ((55, 45, 95), (226, 118, 88), (255, 226, 167)),
    "cel": ((43, 67, 106), (91, 164, 187), (252, 222, 165)),
    "pastel": ((91, 83, 138), (197, 146, 172), (248, 230, 196)),
}


@dataclass(frozen=True)
class AlgorithmicColorizer:
    """Deterministic colorizer used as the default local MVP adapter.

    The class intentionally exposes the same small surface a future ML/API colorizer
    would use, so model integrations can replace it without changing the pipeline.
    """

    palette: str = "sunset"

    def colorize(self, image: Image.Image) -> Image.Image:
        gray = np.asarray(image.convert("L"), dtype=np.float32) / 255.0
        shadow, mid, highlight = _palette(self.palette)

        low_mix = np.clip(gray * 2.0, 0.0, 1.0)[..., None]
        high_mix = np.clip((gray - 0.5) * 2.0, 0.0, 1.0)[..., None]
        low = shadow * (1.0 - low_mix) + mid * low_mix
        high = mid * (1.0 - high_mix) + highlight * high_mix
        color = np.where((gray < 0.5)[..., None], low, high)

        height, width = gray.shape
        x_gradient = np.linspace(0.0, 1.0, width, dtype=np.float32)[None, :, None]
        y_gradient = np.linspace(0.0, 1.0, height, dtype=np.float32)[:, None, None]
        ambient = shadow * (1.0 - x_gradient) + highlight * x_gradient
        ambient = ambient * (0.75 + y_gradient * 0.25)
        color = color * 0.7 + ambient * 0.3

        cel_regions = ((x_gradient * 3).astype(np.int16) + (y_gradient * 2).astype(np.int16)) % 3
        cel_tones = np.where(
            cel_regions == 0,
            shadow,
            np.where(cel_regions == 1, mid, highlight),
        )
        light_area = gray > 0.32
        color[light_area] = color[light_area] * 0.62 + cel_tones[light_area] * 0.38

        paper = np.asarray(image.convert("RGB").filter(ImageFilter.GaussianBlur(radius=1.2)), dtype=np.float32)
        color = color * 0.95 + paper * 0.05

        ink_mask = gray < 0.16
        color[ink_mask] = np.asarray(image.convert("RGB"), dtype=np.float32)[ink_mask] * 0.35

        bubble_mask = gray > 0.985
        color[bubble_mask] = np.asarray(image.convert("RGB"), dtype=np.float32)[bubble_mask] * 0.9 + 255.0 * 0.1

        return Image.fromarray(np.clip(color, 0, 255).astype(np.uint8), mode="RGB")


def _palette(name: str) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if name not in PALETTES:
        available = ", ".join(sorted(PALETTES))
        raise ValueError(f"Unknown palette '{name}'. Available palettes: {available}")
    return tuple(np.asarray(color, dtype=np.float32) for color in PALETTES[name])  # type: ignore[return-value]
