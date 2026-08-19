"""Highlight detection (task 11a).

Spec Section 17: RGB → HSV → color mask (yellow by default) → morphological
cleanup → contours → highlight bbox + polygon. Runs independently from OCR
and never alters OCR text.

The mask is computed on the *rendered* (color) page image, not the ink mask,
because highlight color is not ink.
"""

from __future__ import annotations

import cv2
import numpy as np

from config import CONFIG
from schemas import BoundingBox, Highlight, Point


def detect_highlights(rendered_bgr: np.ndarray, page_number: int) -> tuple[list[Highlight], np.ndarray]:
    """Return (highlights, highlight_mask) for one rendered page.

    The mask is also persisted by the caller as processed/<page>/highlight_mask.png
    (spec Section 36 artifact retention).
    """
    cfg = CONFIG.highlight
    hsv = cv2.cvtColor(rendered_bgr, cv2.COLOR_BGR2HSV)

    lower = np.array([cfg.hue_min, cfg.sat_min, cfg.val_min], dtype=np.uint8)
    upper = np.array([cfg.hue_max, cfg.sat_max, cfg.val_max], dtype=np.uint8)
    mask = cv2.inRange(hsv, lower, upper)

    # morphological cleanup
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (cfg.cleanup_size, cfg.cleanup_size))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    highlights: list[Highlight] = []
    counter = 0
    for contour in contours:
        area = cv2.contourArea(contour)
        if area < cfg.min_area:
            continue
        counter += 1
        x, y, w, h = cv2.boundingRect(contour)
        polygon = [Point(int(px), int(py)) for px, py in cv2.approxPolyDP(contour, 4.0, True).reshape(-1, 2)]
        highlights.append(
            Highlight(
                id=f"highlight_{counter:03d}",
                type="highlight",
                bbox=BoundingBox(x=int(x), y=int(y), width=int(w), height=int(h)),
                polygon=polygon,
            )
        )

    highlights.sort(key=lambda h: (h.bbox.y if h.bbox else 0, h.bbox.x if h.bbox else 0))
    return highlights, mask
