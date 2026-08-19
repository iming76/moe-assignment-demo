"""Caret detection (task 11c).

Spec Section 19: a caret insertion consists of (1) the caret symbol drawn at
the anchor position in the original line, (2) the inserted text written
above/near it, (3) the anchor line id.

Deterministic pattern on ruled paper: the caret symbol is a small isolated
component sitting in the lower part of the line band (it straddles the
baseline), while the inserted text floats in the band region above the
symbol. Both must be present and the inserted text must be short (1-2
words); the anchor line is the line whose band contains the symbol.

POC note: handwriting variance means this heuristic is recall-biased; extra
candidates surface in the review frontend and the optional LLM anchor stage
(design.md risks) rather than silently corrupting the transcription.
"""

from __future__ import annotations

import cv2
import numpy as np

from ..config import CONFIG
from ..imaging.opencv_analysis import LineRegion, clean_mask
from ..schemas import BoundingBox, Caret


def detect_carets(
    ink: np.ndarray,
    line_items: list[tuple[str, LineRegion]],
) -> list[Caret]:
    """Detect caret insertions on one page.

    line_items: (line_id, LineRegion) pairs.
    """
    cfg = CONFIG.caret
    cleaned = clean_mask(ink)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(cleaned, 8)

    small: list[tuple[int, int, int, int, int]] = [
        (int(stats[j][0]), int(stats[j][1]), int(stats[j][2]), int(stats[j][3]), int(stats[j][4]))
        for j in range(1, n)
        if cfg.symbol_min <= stats[j][2] <= cfg.symbol_max
        and cfg.symbol_min <= stats[j][3] <= cfg.symbol_max
        and cfg.symbol_min_area <= stats[j][4] <= cfg.symbol_max_area
    ]

    carets: list[Caret] = []
    counter = 0
    for line_id, line in line_items:
        b = line.bbox
        bottom_edge = b.y + cfg.symbol_bottom_frac * b.height
        for x, y, w, h, area in small:
            cx = x + w / 2
            if not (b.x <= cx <= b.x + b.width):
                continue
            if y < bottom_edge or y + h > b.y + b.height + cfg.symbol_below_slack:
                continue
            top = max(0, y - cfg.insert_above)
            insert_parts = [
                (ix, iy, iw, ih)
                for ix, iy, iw, ih, ia in small
                if top <= iy <= y - cfg.insert_min_above
                and abs((ix + iw / 2) - cx) <= cfg.insert_max_dx
                and (ix, iy, iw, ih) != (x, y, w, h)
            ]
            if not insert_parts:
                continue
            ix0 = min(p[0] for p in insert_parts)
            iy0 = min(p[1] for p in insert_parts)
            ix1 = max(p[0] + p[2] for p in insert_parts)
            iy1 = max(p[1] + p[3] for p in insert_parts)
            if ix1 - ix0 > cfg.insert_max_width or iy1 - iy0 > cfg.insert_max_height:
                continue
            counter += 1
            carets.append(
                Caret(
                    id=f"caret_{counter:03d}",
                    type="caret",
                    caret={"bbox": BoundingBox(x=x, y=y, width=w, height=h).to_json()},
                    insertCrop="",  # filled by crop_generator
                    anchorLineId=line_id,
                    insertBbox=BoundingBox(x=ix0, y=iy0, width=ix1 - ix0, height=iy1 - iy0),
                )
            )

    carets.sort(key=lambda c: (c.caret["bbox"]["y"], c.caret["bbox"]["x"]))
    return carets
