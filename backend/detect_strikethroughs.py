"""Strikethrough detection (task 11b).

Spec Section 18: cancelled text is identified by strokes that cross
handwriting. Signals used (all configurable):

- length: horizontal morphological open keeps only long horizontal runs
  (longer than any single character),
- orientation: near-horizontal strokes (aspect ratio),
- overlap: the stroke sits inside a handwriting line bbox (lineId association),
- crossing: the stroke continues across inter-word gaps (character bars stay
  inside words; a cancellation stroke is drawn across several words).

Strikethroughs on ruled paper are drawn in diagonal multi-pass strokes, so
fragments are joined with a wide+tall dilation before contouring. The ruled
lines themselves are removed from the mask first (they would otherwise be
the longest horizontal structures on the page).

POC note: detection is deterministic-first and intentionally recall-biased;
false positives are expected and resolved in human review (design.md risks),
never silently.
"""

from __future__ import annotations

import cv2
import numpy as np

from config import CONFIG
from opencv_analysis import clean_mask
from schemas import BoundingBox, Strikethrough


def detect_strikethroughs(
    ink: np.ndarray,
    line_items: list[tuple[str, BoundingBox]],
) -> list[Strikethrough]:
    """Find strikethrough candidate strokes inside the given line bboxes.

    line_items: (line_id, bbox) pairs, e.g. the OCRLine ids of the page.
    """
    cfg = CONFIG.strikethrough
    cleaned = clean_mask(ink)
    open_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (cfg.open_kernel, 1))
    join_kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT, (cfg.join_gap, cfg.join_height)
    )

    strikes: list[Strikethrough] = []
    counter = 0

    for line_id, bbox in line_items:
        x0 = max(0, bbox.x)
        y0 = max(0, bbox.y)
        x1 = min(cleaned.shape[1], bbox.x + bbox.width)
        y1 = min(cleaned.shape[0], bbox.y + bbox.height)
        band = cleaned[y0:y1, x0:x1]
        if band.size == 0:
            continue

        strokes = cv2.morphologyEx(band, cv2.MORPH_OPEN, open_kernel)
        # join diagonal multi-pass fragments of the same strike
        strokes = cv2.dilate(strokes, join_kernel)

        contours, _ = cv2.findContours(strokes, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            sx, sy, sw, sh = cv2.boundingRect(contour)
            if sw < cfg.min_stroke_len:
                continue
            if sh > cfg.max_stroke_thickness:
                continue
            if sw < cfg.min_aspect * max(1, sh):
                continue
            if _max_crossed_gap(band, sx, sy, sw, sh) < cfg.min_crossed_gap:
                continue
            counter += 1
            stroke_bbox = BoundingBox(x=x0 + sx, y=y0 + sy, width=sw, height=sh)
            strikes.append(
                Strikethrough(
                    id=f"strike_{counter:03d}",
                    type="strikethrough",
                    bbox=stroke_bbox,
                    strokeBbox=stroke_bbox,
                    lineId=line_id,
                )
            )

    strikes.sort(key=lambda s: (s.bbox.y if s.bbox else 0, s.bbox.x if s.bbox else 0))
    return strikes


def _max_crossed_gap(band: np.ndarray, sx: int, sy: int, sw: int, sh: int) -> int:
    """Longest horizontal run where the stroke crosses an inter-word gap.

    A gap column has no ink outside the stroke rows; a crossed gap column
    additionally has ink inside the stroke rows.
    """
    outside = band.copy()
    outside[max(0, sy - 1) : sy + sh + 1, :] = 0
    gap_cols = (outside > 0).sum(axis=0) == 0
    stroke_rows = band[sy : sy + sh, :] > 0

    best = run = 0
    for gx in range(sx, min(band.shape[1], sx + sw)):
        if gap_cols[gx] and stroke_rows[:, gx].any():
            run += 1
            best = max(best, run)
        else:
            run = 0
    return best
