"""Paragraph boundary detection and splitting (task 10).

Spec Section 12: weighted score over vertical gap (primary), indentation and
density (secondary). Runs before detailed OCR; each paragraph gets a unique
id (p001, p002, ...), an order, and one crop region.

Conceptual score (spec): 0.55*gap + 0.25*indent + 0.20*density, weights
configurable. Each signal is normalized to [0, 1] against page statistics;
a boundary is emitted when the score crosses paragraph.threshold.
"""

from __future__ import annotations

from ..config import CONFIG
from ..imaging.opencv_analysis import LineRegion, handwriting_density, median_line_height
from ..schemas import BoundingBox, Paragraph


def _vertical_gap(a: LineRegion, b: LineRegion) -> float:
    return float(b.bbox.y - (a.bbox.y + a.bbox.height))


def detect_paragraphs(
    lines: list[LineRegion],
    ink,
    page_number: int,
    answer_bbox: BoundingBox | None = None,
) -> list[Paragraph]:
    """Split the given lines (already restricted to the answer region) into
    logical paragraphs, ordered top to bottom."""
    cfg = CONFIG.paragraph
    ordered = sorted(lines, key=lambda ln: ln.bbox.y)
    if not ordered:
        return []

    median_h = median_line_height(ordered) or 1.0
    left_x = min(ln.bbox.x for ln in ordered)
    widths = [ln.bbox.width for ln in ordered]
    full_w = float(max(widths)) or 1.0

    boundaries: list[int] = []  # index i starts a new paragraph
    for i in range(1, len(ordered)):
        prev, cur = ordered[i - 1], ordered[i]
        gap = _vertical_gap(prev, cur)

        # normalized signals in [0, 1]
        gap_score = min(1.0, max(0.0, gap / (cfg.gap_multiple * median_h)))
        indent = cur.bbox.x - left_x
        indent_score = min(1.0, max(0.0, indent / (0.25 * full_w)))
        prev_density = handwriting_density(ink, prev.bbox)
        cur_density = handwriting_density(ink, cur.bbox)
        density_score = min(1.0, abs(prev_density - cur_density) * 4.0)

        w = cfg.weights
        score = (
            w.vertical_gap * gap_score
            + w.indentation * indent_score
            + w.density * density_score
        )
        if score >= cfg.threshold:
            boundaries.append(i)

    starts = [0] + boundaries
    paragraphs: list[Paragraph] = []
    for order, start in enumerate(starts, 1):
        end = starts[order] if order < len(starts) else len(ordered)
        group = ordered[start:end]
        x0 = min(ln.bbox.x for ln in group)
        y0 = min(ln.bbox.y for ln in group)
        x1 = max(ln.bbox.x + ln.bbox.width for ln in group)
        y1 = max(ln.bbox.y + ln.bbox.height for ln in group)
        paragraphs.append(
            Paragraph(
                id=f"p{order:03d}",
                pageNumber=page_number,
                order=order,
                bbox=BoundingBox(x=x0, y=y0, width=x1 - x0, height=y1 - y0),
                cropPath="",  # filled by crop_generator
                lines=[],
                highlights=[],
                text="",
            )
        )
    return paragraphs
