"""Question detection + multi-line grouping (tasks 7 & 8).

Spec Sections 7-9. The question is recorded before answer processing.

Signals (task 7): Q1/Q2/QN 1/Question prefixes and question marks (when OCR
text is available), plus position and spacing signals (always): the question
is the first content line after the page header, separated from the answer by
a paragraph-scale gap.

Grouping (task 8): physical lines of one question merge into a single
Question with no internal line breaks; continuation lines are short lines
that do not reach the full writing width and sit within the grouping gap.
"""

from __future__ import annotations

import re
from typing import Callable, Optional

from ..config import CONFIG
from ..imaging.opencv_analysis import LineRegion, median_line_height
from ..schemas import BoundingBox, Question

QUESTION_PREFIX_RE = re.compile(
    r"^\s*(Q\s*\d+|QN\s*\d+|Question\s*\d*\b)", re.IGNORECASE
)


def _is_header_line(line: LineRegion, median_h: float) -> bool:
    """Tall blocks at the top (logo/printed header) are not handwriting lines."""
    return line.bbox.height > CONFIG.question.header_height_factor * median_h


def _full_width(lines: list[LineRegion]) -> float:
    widths = sorted(ln.bbox.width for ln in lines)
    if not widths:
        return 0.0
    return float(widths[len(widths) // 2])


def detect_questions(
    lines: list[LineRegion],
    page_number: int,
    text_for: Optional[Callable[[LineRegion], str]] = None,
) -> list[Question]:
    """Detect question line groups on one page.

    text_for, when provided, supplies OCR text so prefix/question-mark
    signals can confirm the spatial guess; without it, position + spacing
    alone decide (question detection runs before detailed OCR).
    """
    cfg = CONFIG.question
    median_h = median_line_height(lines)
    if median_h <= 0:
        return []
    content = [ln for ln in lines if not _is_header_line(ln, median_h)]
    if not content:
        return []

    full_w = _full_width(content)
    questions: list[Question] = []
    index = 0
    q_counter = 0

    while index < len(content):
        first = content[index]
        text = text_for(first) if text_for else ""
        prefix_hit = bool(QUESTION_PREFIX_RE.match(text)) if text else False
        qmark_hit = "?" in text if text else False

        # Spatial guess: the first content line of the page starts the
        # question (position + spacing signal). Any later line only counts as
        # a new question when OCR text confirms it via prefix or question
        # mark. The question is recorded before answer processing.
        is_question = (index == 0) or prefix_hit or qmark_hit

        if not is_question:
            index += 1
            continue

        group = [first]
        cursor = index + 1
        while cursor < len(content):
            nxt = content[cursor]
            gap = nxt.bbox.y - (group[-1].bbox.y + group[-1].bbox.height)
            nxt_text = text_for(nxt) if text_for else ""
            starts_new_question = bool(QUESTION_PREFIX_RE.match(nxt_text)) if nxt_text else False
            is_short = nxt.bbox.width < cfg.short_line_ratio * full_w
            if gap <= cfg.group_max_gap and is_short and not starts_new_question:
                group.append(nxt)
                cursor += 1
            else:
                break

        q_counter += 1
        qid = f"q{q_counter:03d}"
        bbox = _union([ln.bbox for ln in group])
        questions.append(
            Question(
                id=qid,
                bbox=bbox,
                cropPath="",  # filled by crop_generator
                lines=[f"{qid}_line{i + 1:03d}" for i in range(len(group))],
                text="",      # filled after OCR
            )
        )
        index = cursor
        # Only the first question group per page is expected in the POC
        # sample; keep scanning for more questions further down the page.
    return questions


def _union(bboxes: list[BoundingBox]) -> BoundingBox:
    x0 = min(b.x for b in bboxes)
    y0 = min(b.y for b in bboxes)
    x1 = max(b.x + b.width for b in bboxes)
    y1 = max(b.y + b.height for b in bboxes)
    return BoundingBox(x=x0, y=y0, width=x1 - x0, height=y1 - y0)
