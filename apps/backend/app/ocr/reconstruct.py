"""Line-only OCR reconstruction.

Physical OCR lines are joined with spaces inside a paragraph. Paragraphs are
separated by blank lines. No caret or strikethrough interpretation is applied.
"""

from __future__ import annotations

import difflib
import re

from ..config import CONFIG
from ..schemas import Document, OCRResult, Paragraph

_TAG_RE = re.compile(r"</?(strikethrough|caret)>")
_SPACE_RE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    """Strip markup tags and collapse whitespace, for text-only comparison."""
    return _SPACE_RE.sub(" ", _TAG_RE.sub("", text)).strip().lower()


def reconcile_paragraph_ocr(
    paragraph: Paragraph,
    line_text: str,
    paragraph_result: OCRResult | None,
    ocr_by_crop: dict[str, OCRResult],
) -> None:
    """Cross-check line-level OCR against a paragraph-level OCR pass.

    Line OCR stays the source of truth (never overwritten here). When the two
    disagree past ``paragraph_match_threshold``, escalate any line in this
    paragraph still at ``reviewState == "pending"`` (i.e. not already flagged
    for a more specific reason) so a human reviewer sees the mismatch.
    """
    if paragraph_result is None or not paragraph_result.text.strip():
        return
    if not line_text.strip():
        return
    ratio = difflib.SequenceMatcher(
        None, _normalize(line_text), _normalize(paragraph_result.text)
    ).ratio()
    if ratio >= CONFIG.confidence.paragraph_match_threshold:
        return
    for line in paragraph.lines:
        result = ocr_by_crop.get(line.cropId)
        if result is not None and result.reviewState == "pending":
            result.reviewState = "required"
            result.reviewRequiredReason = "line_paragraph_mismatch"


def reconstruct_paragraph(
    paragraph: Paragraph,
    ocr_by_crop: dict[str, OCRResult],
) -> str:
    """Return literal OCR text for the paragraph in reading order."""
    line_texts: list[str] = []
    for line in paragraph.lines:
        result = ocr_by_crop.get(line.cropId)
        raw = result.text if result else line.text
        if raw.strip():
            line_texts.append(raw.strip())
    return " ".join(line_texts)


def reconstruct_document(document: Document, ink_by_page: dict | None = None) -> Document:
    """Fill paragraph text and final output from line-level OCR results."""
    del ink_by_page  # Retained for compatibility with existing callers.
    questions: list[str] = []
    answers: list[str] = []

    for page in document.pages:
        ocr_by_crop = {result.cropId: result for result in page.ocr}
        paragraph_ocr_by_crop = {result.cropId: result for result in page.paragraphOcr}
        if page.question is not None:
            questions.append(page.question.text)
        if page.answer is not None:
            paragraph_texts: list[str] = []
            for paragraph in page.answer.paragraphs:
                paragraph.text = reconstruct_paragraph(paragraph, ocr_by_crop)
                reconcile_paragraph_ocr(
                    paragraph,
                    paragraph.text,
                    paragraph_ocr_by_crop.get(paragraph.id),
                    ocr_by_crop,
                )
                if paragraph.text:
                    paragraph_texts.append(paragraph.text)
            answers.append("\n\n".join(paragraph_texts))

    document.final.question = "\n".join(questions)
    document.final.answer = "\n\n".join(text for text in answers if text)
    return document
