"""Shared OpenCV helpers: line/word segmentation + density (spatial side).

OpenCV determines *where*, never *what*. These helpers consume the ink mask
produced by normalize_image and return bounding boxes in rendered-page
coordinates (document-ingestion: coordinate system consistency).

Ruled paper is expected: full-width thin horizontal rules are removed from
the mask before projection-profile line segmentation.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from ..config import CONFIG
from ..schemas import BoundingBox


@dataclass
class LineRegion:
    """One physical handwriting line, in rendered-page coordinates."""

    bbox: BoundingBox
    ink_area: int  # ink pixel count inside the bbox


def ruled_line_bands(ink: np.ndarray) -> list[tuple[int, int]]:
    """Return inclusive vertical spans of full-width ruled-paper lines."""
    cfg = CONFIG.segment
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (cfg.rule_kernel_width, 1))
    rules = cv2.morphologyEx(ink, cv2.MORPH_OPEN, kernel)
    rules = cv2.dilate(rules, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 3)))
    active_rows = (rules > 0).any(axis=1)

    bands: list[tuple[int, int]] = []
    start: int | None = None
    for y, active in enumerate(active_rows):
        if active and start is None:
            start = y
        elif not active and start is not None:
            bands.append((start, y - 1))
            start = None
    if start is not None:
        bands.append((start, len(active_rows) - 1))
    return _merge_close_bands(bands, cfg.rule_merge_gap)


def _merge_close_bands(
    bands: list[tuple[int, int]], gap_tolerance: int
) -> list[tuple[int, int]]:
    """Merge bands separated by a small gap (a rule broken by crossing ink)."""
    if not bands:
        return bands
    merged = [bands[0]]
    for start, end in bands[1:]:
        prev_start, prev_end = merged[-1]
        if start - prev_end - 1 <= gap_tolerance:
            merged[-1] = (prev_start, end)
        else:
            merged.append((start, end))
    return merged


def remove_ruled_lines(ink: np.ndarray) -> np.ndarray:
    """Zero out full-width thin horizontal rules (ruled paper).

    Rules are extracted with a wide horizontal morphological open (they are
    the only structures with long continuous horizontal runs), then
    subtracted. Handwriting never survives a 60px-wide horizontal open.
    """
    cfg = CONFIG.segment
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (cfg.rule_kernel_width, 1))
    rules = cv2.morphologyEx(ink, cv2.MORPH_OPEN, kernel)
    # Recover the full rule thickness around the extracted centre line.
    rules = cv2.dilate(rules, cv2.getStructuringElement(cv2.MORPH_RECT, (1, 3)))
    return cv2.subtract(ink, rules)


def remove_margin_lines(ink: np.ndarray) -> np.ndarray:
    """Zero out full-height thin vertical margin lines (ruled paper)."""
    cfg = CONFIG.segment
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, cfg.margin_kernel_height))
    margins = cv2.morphologyEx(ink, cv2.MORPH_OPEN, kernel)
    margins = cv2.dilate(margins, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 1)))
    return cv2.subtract(ink, margins)


def clean_mask(ink: np.ndarray) -> np.ndarray:
    """Remove ruled lines and crop the analysis region to the page margins.

    Ruled paper also carries thin vertical margin lines at the page edges;
    they are broken by scanning so morphological removal is unreliable.
    Content never reaches the extreme edges, so a configurable crop margin
    (segment.page_crop_*) zeroes them out instead.
    """
    cfg = CONFIG.segment
    cleaned = remove_margin_lines(remove_ruled_lines(ink))
    height, width = cleaned.shape[:2]
    left = min(cfg.page_crop_left, width)
    right = min(cfg.page_crop_right, width)
    top = min(cfg.page_crop_top, height)
    bottom = min(cfg.page_crop_bottom, height)
    if left or right or top or bottom:
        cleaned = cleaned.copy()
        if left:
            cleaned[:, :left] = 0
        if right:
            cleaned[:, width - right :] = 0
        if top:
            cleaned[:top, :] = 0
        if bottom:
            cleaned[height - bottom :, :] = 0
    return cleaned


def segment_lines(ink: np.ndarray, min_ink_area: int | None = None) -> list[LineRegion]:
    """Horizontal projection-profile segmentation into physical lines.

    Returns lines sorted top-to-bottom.
    """
    cfg = CONFIG.segment
    height, width = ink.shape[:2]
    cleaned = clean_mask(ink)
    row_ink = (cleaned > 0).sum(axis=1)

    min_row_ink = max(cfg.min_row_ink, 1)
    lines: list[LineRegion] = []
    run_start = None
    gap = 0

    for y in range(height + 1):
        active = y < height and row_ink[y] >= min_row_ink
        if active:
            if run_start is None:
                run_start = y
            gap = 0
        else:
            if run_start is not None:
                gap += 1
                if gap > cfg.line_gap_tolerance:
                    lines.append(_line_from_rows(cleaned, run_start, y - gap))
                    run_start = None
                    gap = 0
    if run_start is not None:
        lines.append(_line_from_rows(cleaned, run_start, height - 1))

    threshold = min_ink_area if min_ink_area is not None else cfg.min_line_ink_area
    lines = [ln for ln in lines if ln.ink_area >= threshold]
    lines.sort(key=lambda ln: ln.bbox.y)
    return lines


def _line_from_rows(ink: np.ndarray, y0: int, y1: int) -> LineRegion:
    band = ink[y0 : y1 + 1, :]
    cols = np.nonzero(band.any(axis=0))[0]
    x0, x1 = int(cols.min()), int(cols.max())
    ink_area = int((band > 0).sum())
    return LineRegion(
        bbox=BoundingBox(x=x0, y=y0, width=x1 - x0 + 1, height=y1 - y0 + 1),
        ink_area=ink_area,
    )


def segment_words(ink: np.ndarray, line_bbox: BoundingBox) -> list[BoundingBox]:
    """Vertical projection-profile word segmentation inside one line."""
    cfg = CONFIG.segment
    band = ink[
        line_bbox.y : line_bbox.y + line_bbox.height,
        line_bbox.x : line_bbox.x + line_bbox.width,
    ]
    col_ink = (band > 0).sum(axis=0)
    min_col_ink = cfg.min_col_ink
    words: list[BoundingBox] = []
    run_start = None
    gap = 0

    for x in range(band.shape[1] + 1):
        active = x < band.shape[1] and col_ink[x] >= min_col_ink
        if active:
            if run_start is None:
                run_start = x
            gap = 0
        else:
            if run_start is not None:
                gap += 1
                if gap > cfg.word_gap_tolerance:
                    words.append(_word_from_cols(band, run_start, x - gap, line_bbox))
                    run_start = None
                    gap = 0
    if run_start is not None:
        words.append(_word_from_cols(band, run_start, band.shape[1] - 1, line_bbox))

    return [w for w in words if w.width >= cfg.min_word_width]


def _word_from_cols(
    band: np.ndarray, x0: int, x1: int, line_bbox: BoundingBox
) -> BoundingBox:
    sub = band[:, x0 : x1 + 1]
    rows = np.nonzero(sub.any(axis=1))[0]
    y0, y1 = int(rows.min()), int(rows.max())
    return BoundingBox(
        x=line_bbox.x + x0,
        y=line_bbox.y + y0,
        width=x1 - x0 + 1,
        height=y1 - y0 + 1,
    )


def handwriting_density(ink: np.ndarray, bbox: BoundingBox) -> float:
    """Ink pixels / bbox area, clamped to [0, 1]."""
    h, w = ink.shape[:2]
    x0 = max(0, bbox.x)
    y0 = max(0, bbox.y)
    x1 = min(w, bbox.x + bbox.width)
    y1 = min(h, bbox.y + bbox.height)
    area = max(1, (x1 - x0) * (y1 - y0))
    return float((ink[y0:y1, x0:x1] > 0).sum() / area)


def median_line_height(lines: list[LineRegion]) -> float:
    if not lines:
        return 0.0
    heights = sorted(ln.bbox.height for ln in lines)
    return float(heights[len(heights) // 2])
