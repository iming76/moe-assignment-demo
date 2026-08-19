"""Answer region detection (task 9).

Spec Section 10: the answer starts after the question region and associated
spacing, using vertical position, blank-line spacing, handwriting density,
the question bounding box, line grouping and indentation; page headers are
excluded. Headers sit above the question, so position alone excludes them.

Signals used here:
- vertical position / blank spacing: lines between the question bottom and
  the next question top form the candidate region;
- handwriting density: stray low-density lines at the region edges (specks,
  scan noise) are trimmed;
- indentation: left-margin scribbles (lines starting well left of the
  content margin with little ink) are not answer content.
"""

from __future__ import annotations

from ..config import CONFIG
from ..imaging.opencv_analysis import LineRegion, handwriting_density
from ..schemas import Answer, BoundingBox, Question


def _median(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    return float(ordered[len(ordered) // 2])


def detect_answer(
    lines: list[LineRegion],
    questions: list[Question],
    page_number: int,
    ink=None,
) -> Answer | None:
    """Return the answer region for the page (None when no content follows)."""
    if not lines or not questions:
        return None
    cfg = CONFIG.answer

    first_q = min(questions, key=lambda q: q.bbox.y)
    q_bottom = first_q.bbox.y + first_q.bbox.height

    # next question (if any) caps this answer region
    later = [q for q in questions if q.bbox.y > q_bottom]
    cap = min((q.bbox.y for q in later), default=None)

    candidates = [
        ln
        for ln in lines
        if ln.bbox.y > q_bottom
        and (cap is None or ln.bbox.y < cap)
    ]
    if not candidates:
        return None

    if ink is not None:
        # density trim: drop stray low-density specks at the region edges
        densities = [handwriting_density(ink, ln.bbox) for ln in candidates]
        med_density = _median(densities)
        if med_density > 0:
            candidates = [
                ln
                for ln, d in zip(candidates, densities)
                if d >= cfg.trim_density_ratio * med_density
            ]

        # indentation: exclude left-margin scribbles (start well left of the
        # content margin with little ink)
        left_med = _median([float(ln.bbox.x) for ln in candidates])
        candidates = [
            ln
            for ln in candidates
            if not (
                ln.bbox.x < left_med - cfg.margin_scribble_px
                and ln.ink_area < cfg.min_ink_area
            )
        ]

    if not candidates:
        return None

    x0 = min(ln.bbox.x for ln in candidates)
    y0 = min(ln.bbox.y for ln in candidates)
    x1 = max(ln.bbox.x + ln.bbox.width for ln in candidates)
    y1 = max(ln.bbox.y + ln.bbox.height for ln in candidates)

    return Answer(bbox=BoundingBox(x=x0, y=y0, width=x1 - x0, height=y1 - y0), paragraphs=[])


def answer_line_regions(
    lines: list[LineRegion], answer: Answer
) -> list[LineRegion]:
    """The physical lines inside the answer bbox, top to bottom."""
    return [
        ln
        for ln in sorted(lines, key=lambda l: l.bbox.y)
        if answer.bbox.y <= ln.bbox.y <= answer.bbox.y + answer.bbox.height
    ]
