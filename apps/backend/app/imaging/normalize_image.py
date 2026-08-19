"""Image preprocessing pipeline (task 6).

Spec Section 16 pipeline:

    rendered page → grayscale → denoise → contrast normalization →
    deskew → adaptive threshold → morphological cleanup

All intermediates are persisted to processed/<page>/ (spec Section 37 names:
grayscale.png, deskew.png, binary.png). The rendered page image stays
available untouched — every later bbox is expressed in its coordinate
system, so deskew is applied to analysis images only, never to the rendered
page itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from ..config import CONFIG
from ..schemas import PageImage
from ..storage import StorageLayout


@dataclass
class PreprocessResult:
    """Relative paths of persisted intermediates + measured deskew angle."""

    grayscale_path: str
    deskew_path: str
    binary_path: str
    deskew_angle_deg: float
    extras: dict[str, str] = field(default_factory=dict)


def _deskew_angle(binary_inverse: np.ndarray) -> float:
    """Estimate page skew from ink pixels; clamped to the configured bound.

    Uses the minimum-area rectangle over ink foreground. Returns the rotation
    angle (degrees) that would level the handwriting.
    """
    ys, xs = np.nonzero(binary_inverse)
    if len(xs) < 200:
        return 0.0
    points = np.column_stack((xs, ys)).astype(np.float32)
    angle = cv2.minAreaRect(points)[-1]
    # minAreaRect returns angles in [-90, 0); map to a small skew offset.
    if angle < -45:
        angle = 90 + angle
    angle = -angle
    limit = CONFIG.preprocess.max_deskew_deg
    return float(max(-limit, min(limit, angle)))


def _rotate(image: np.ndarray, angle_deg: float) -> np.ndarray:
    if abs(angle_deg) < 0.05:
        return image
    h, w = image.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle_deg, 1.0)
    return cv2.warpAffine(
        image, m, (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )


def preprocess_page(page: PageImage, layout: StorageLayout) -> PreprocessResult:
    """Run the full preprocessing pipeline for one rendered page.

    Reads layout.rendered_path(page.pageNumber) and writes intermediates into
    layout.processed_page(page.pageNumber).
    """
    out_dir = layout.processed_page(page.pageNumber)
    out_dir.mkdir(parents=True, exist_ok=True)

    rendered = cv2.imread(str(layout.rendered_path(page.pageNumber)), cv2.IMREAD_COLOR)
    if rendered is None:
        raise FileNotFoundError(f"Rendered page not found: {layout.rendered_path(page.pageNumber)}")

    cfg = CONFIG.preprocess

    # 1. Grayscale
    gray = cv2.cvtColor(rendered, cv2.COLOR_BGR2GRAY)
    grayscale_path = out_dir / "grayscale.png"
    cv2.imwrite(str(grayscale_path), gray)

    # 2. Denoise (edge-preserving)
    denoised = cv2.fastNlMeansDenoising(gray, None, h=cfg.denoise_h,
                                        templateWindowSize=7, searchWindowSize=21)

    # 3. Contrast normalization (CLAHE)
    clahe = cv2.createCLAHE(clipLimit=cfg.clahe_clip_limit,
                            tileGridSize=(cfg.clahe_grid, cfg.clahe_grid))
    normalized = clahe.apply(denoised)

    # 4. Deskew — estimate from a quick Otsu binarization of the normalized
    #    image, then rotate the analysis image. Rendered page stays untouched.
    _, otsu_inverse = cv2.threshold(normalized, 0, 255,
                                    cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    angle = _deskew_angle(otsu_inverse)
    deskewed = _rotate(normalized, angle)
    deskew_path = out_dir / "deskew.png"
    cv2.imwrite(str(deskew_path), deskewed)

    # 5. Adaptive threshold — ink becomes black on white (foreground-friendly)
    binary = cv2.adaptiveThreshold(
        deskewed, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY,
        blockSize=cfg.adaptive_block_size, C=cfg.adaptive_c,
    )
    binary_path = out_dir / "binary.png"
    cv2.imwrite(str(binary_path), binary)

    # 6. Morphological cleanup on the ink mask (binary inverse):
    #    close small gaps inside strokes, drop speckle noise.
    ink = cv2.bitwise_not(binary)
    kernel_close = cv2.getStructuringElement(
        cv2.MORPH_RECT, (cfg.morph_close_size, cfg.morph_close_size))
    kernel_open = cv2.getStructuringElement(
        cv2.MORPH_RECT, (cfg.morph_open_size, cfg.morph_open_size))
    ink = cv2.morphologyEx(ink, cv2.MORPH_CLOSE, kernel_close)
    ink = cv2.morphologyEx(ink, cv2.MORPH_OPEN, kernel_open)
    ink_mask_path = out_dir / "ink_mask.png"
    cv2.imwrite(str(ink_mask_path), ink)

    return PreprocessResult(
        grayscale_path=layout.rel(grayscale_path),
        deskew_path=layout.rel(deskew_path),
        binary_path=layout.rel(binary_path),
        deskew_angle_deg=angle,
        extras={"ink_mask": layout.rel(ink_mask_path)},
    )
