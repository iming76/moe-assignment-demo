"""Reconstruction engine (task 14).

Spec Sections 26-30: merges OCR text with spatial + markup metadata.

- caret text inserted at its logical position, wrapped in <caret>
- cancelled text wrapped in <strikethrough>, kept visible
- physical line breaks joined with single spaces
- paragraphs separated by \n\n
- full internal JSON assembled (documentId, source, pages, final)

Word-level alignment: line OCR text is tokenized on whitespace and mapped
onto the line's word bboxes in reading order; when counts differ the markup
falls back to whole-line wrapping (never guesses word splits).
"""

from __future__ import annotations

from config import CONFIG
from opencv_analysis import segment_words
from schemas import (
    BoundingBox,
    Caret,
    Document,
    OCRResult,
    Paragraph,
    Strikethrough,
)

CARET_OPEN = "<caret>"
CARET_CLOSE = "</caret>"
STRIKE_OPEN = "<strikethrough>"
STRIKE_CLOSE = "</strikethrough>"


def _inter_word_gaps(words: list[BoundingBox]) -> list[float]:
    """x positions of the gaps between consecutive words."""
    gaps = []
    for a, b in zip(words, words[1:]):
        gaps.append((a.x + a.width + b.x) / 2.0)
    return gaps


def anchor_caret_deterministic(
    caret: Caret,
    words: list[BoundingBox],
) -> tuple[int, bool, list[int]]:
    """Project the caret tip x onto the nearest inter-word gap.

    Returns (gap_index, ambiguous, candidate_indices). Ambiguity per spec
    39.1.2: two gaps within gap_epsilon_px of the projection.
    """
    if not caret.caret.get("bbox") or len(words) < 2:
        return 0, False, []
    cx = caret.caret["bbox"]["x"] + caret.caret["bbox"]["width"] / 2.0
    gaps = _inter_word_gaps(words)
    if not gaps:
        return 0, False, []
    dists = [abs(g - cx) for g in gaps]
    best = int(min(range(len(gaps)), key=lambda i: dists[i]))
    eps = CONFIG.caret_anchor.gap_epsilon_px
    near = [i for i, d in enumerate(dists) if abs(d - dists[best]) <= eps]
    ambiguous = len(near) > 1
    return best, ambiguous, near if ambiguous else []


def _align_tokens(text: str, words: list[BoundingBox]) -> list[str] | None:
    tokens = text.split()
    if len(tokens) == len(words) and tokens:
        return tokens
    return None


def reconstruct_line(
    line_text: str,
    words: list[BoundingBox],
    strikes: list[Strikethrough],
    caret_inserts: list[tuple[int, str]],  # (gap_index, inserted text)
) -> str:
    """One physical line with markup applied."""
    tokens = _align_tokens(line_text, words)
    if tokens is None:
        out = line_text
        # whole-line fallback for strikethroughs
        if any(s.bbox is not None for s in strikes) and line_text.strip():
            out = f"{STRIKE_OPEN}{line_text}{STRIKE_CLOSE}"
        for _, inserted in caret_inserts:
            out = f"{out} {CARET_OPEN}{inserted}{CARET_CLOSE}"
        return out

    pieces: list[str] = []
    for idx, token in enumerate(tokens):
        wrapped = token
        for strike in strikes:
            if strike.bbox is None or idx >= len(words):
                continue
            w = words[idx]
            overlap = min(w.x + w.width, strike.bbox.x + strike.bbox.width) - max(
                w.x, strike.bbox.x
            )
            if overlap > 0.5 * min(w.width, strike.bbox.width):
                wrapped = f"{STRIKE_OPEN}{wrapped}{STRIKE_CLOSE}"
        pieces.append(wrapped)
        for gap_idx, inserted in caret_inserts:
            if gap_idx == idx:  # after token idx
                pieces.append(f"{CARET_OPEN}{inserted}{CARET_CLOSE}")

    return " ".join(pieces)


def reconstruct_paragraph(
    paragraph: Paragraph,
    ocr_by_crop: dict[str, OCRResult],
    carets: list[Caret],
    ink=None,
) -> str:
    """Paragraph text: lines joined with spaces, markup applied."""
    line_texts: list[str] = []
    for line in paragraph.lines:
        result = ocr_by_crop.get(line.cropId)
        raw = result.text if result else line.text
        words = segment_words(ink, line.bbox) if ink is not None else []

        strikes = [
            m
            for m in paragraph.markups
            if isinstance(m, Strikethrough)
            and (m.lineId == line.id or _intersects(m.bbox, line.bbox))
        ]
        inserts: list[tuple[int, str]] = []
        for caret in carets:
            if caret.anchorLineId != line.id:
                continue
            inserted = ocr_by_crop.get(caret.id)
            inserted_text = inserted.text if inserted else ""
            gap_idx, _ambiguous, _cands = anchor_caret_deterministic(caret, words)
            inserts.append((gap_idx, inserted_text))

        line_texts.append(reconstruct_line(raw, words, strikes, inserts))

    return " ".join(t for t in line_texts if t.strip())


def _intersects(a: BoundingBox | None, b: BoundingBox) -> bool:
    if a is None:
        return False
    return not (
        a.x + a.width < b.x
        or b.x + b.width < a.x
        or a.y + a.height < b.y
        or b.y + b.height < a.y
    )


def reconstruct_document(document: Document, ink_by_page: dict | None = None) -> Document:
    """Fill paragraph.text and document.final (spec Sections 29-31)."""
    ink_by_page = ink_by_page or {}
    questions: list[str] = []
    answers: list[str] = []

    for page in document.pages:
        ocr_by_crop = {o.cropId: o for o in page.ocr}
        if page.question is not None:
            questions.append(page.question.text)
        if page.answer is not None:
            para_texts = []
            for para in page.answer.paragraphs:
                para.text = reconstruct_paragraph(
                    para, ocr_by_crop, page.carets, ink_by_page.get(page.pageNumber)
                )
                para_texts.append(para.text)
            answers.append("\n\n".join(t for t in para_texts if t))

    document.final.question = "\n".join(questions)
    document.final.answer = "\n\n".join(answers)
    return document
