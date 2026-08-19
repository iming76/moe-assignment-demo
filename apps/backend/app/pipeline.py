"""Pipeline orchestrator (task 17).

One short orchestrator wiring the stage modules in order and advancing the
document state machine per stage (spec Section 40):

    UPLOADED → NORMALIZED → QUESTION_DETECTED → ANSWER_DETECTED →
    PARAGRAPHS_DETECTED → CROPS_GENERATED → OCR_PROCESSING →
    MARKUP_RECONSTRUCTION → REVIEW_REQUIRED → APPROVED → EXPORTED

Every artifact is retained in the storage layout (spec Sections 36-37).
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import cv2

from .config import CONFIG
from .imaging.crop_generator import generate_crops
from .detect.answers import answer_line_regions, detect_answer
from .detect.carets import detect_carets
from .detect.highlights import detect_highlights
from .detect.paragraphs import detect_paragraphs
from .detect.questions import detect_questions
from .detect.strikethroughs import detect_strikethroughs
from .ocr.llm_review import run_llm_review
from .imaging.normalize_image import preprocess_page
from .imaging.opencv_analysis import median_line_height, segment_lines, segment_words
from .ingest.pages import ingest_document
from .ocr.reconstruct import reconstruct_document
from .review import enter_review, export_document
from .ocr.trocr import persist_ocr, run_line_crop
from .schemas import Document
from .state_machine import transition
from .storage import StorageLayout


def _imread(path: Path, flags: int = cv2.IMREAD_COLOR):
    image = cv2.imread(str(path), flags)
    if image is None:
        raise FileNotFoundError(f"Image not found: {path}")
    return image


def process_document(
    source_path: Path,
    document_id: str,
    root: str | None = None,
    on_state_change: Callable[[str], None] | None = None,
    on_ocr_progress: Callable[[int, int], None] | None = None,
) -> Document:
    """Run the full pipeline to REVIEW_REQUIRED and return the document.

    ``on_state_change`` is invoked with the new state string after every
    transition, letting callers (e.g. an SSE endpoint) stream stage progress.
    ``on_ocr_progress`` is invoked with (completed, total) after each crop is
    transcribed during OCR_PROCESSING, the pipeline's slowest stage.
    """
    layout = StorageLayout(document_id, root=root)

    def advance(current: str, next_state: str) -> str:
        state = transition(current, next_state)
        if on_state_change is not None:
            on_state_change(state)
        return state

    # UPLOADED → NORMALIZED
    source, pages_meta = ingest_document(source_path, layout)
    document = Document(documentId=document_id, source=source, state="UPLOADED")
    document.state = advance(document.state, "NORMALIZED")

    for page_meta in pages_meta:
        from .schemas import DocumentPage

        page = DocumentPage(pageNumber=page_meta.pageNumber, image=page_meta)
        preprocess = preprocess_page(page_meta, layout)

        # persist highlight mask (spec Section 36 artifact retention)
        rendered = _imread(layout.rendered_path(page_meta.pageNumber))
        highlights, hmask = detect_highlights(rendered, page_meta.pageNumber)
        cv2.imwrite(str(layout.processed_page(page_meta.pageNumber) / "highlight_mask.png"), hmask)
        page.highlights = highlights

        ink = _imread(
            layout.processed_page(page_meta.pageNumber) / "ink_mask.png",
            cv2.IMREAD_GRAYSCALE,
        )

        # NORMALIZED → QUESTION_DETECTED
        lines = segment_lines(ink)
        questions = detect_questions(lines, page_meta.pageNumber)
        document.state = advance(document.state, "QUESTION_DETECTED")
        page.question = questions[0] if questions else None

        # → ANSWER_DETECTED
        answer = detect_answer(lines, questions, page_meta.pageNumber, ink)
        document.state = advance(document.state, "ANSWER_DETECTED")
        page.answer = answer

        # → PARAGRAPHS_DETECTED
        if answer is not None:
            answer.paragraphs = detect_paragraphs(
                answer_line_regions(lines, answer), ink, page_meta.pageNumber, answer.bbox
            )
        document.state = advance(document.state, "PARAGRAPHS_DETECTED")

        # markup detection (spatial side, before OCR)
        content = [
            (f"line{i:03d}", lr)
            for i, lr in enumerate(lines)
            if lr.bbox.height <= CONFIG.question.header_height_factor * median_line_height(lines)
        ]
        strikes = detect_strikethroughs(ink, [(lid, lr.bbox) for lid, lr in content])
        if answer is not None:
            for strike in strikes:
                for para in answer.paragraphs:
                    if para.bbox.y <= strike.bbox.y <= para.bbox.y + para.bbox.height:
                        para.markups.append(strike)
                        break
        page.carets = detect_carets(ink, content)

        # → CROPS_GENERATED (all crops persisted BEFORE any OCR)
        generate_crops(page, rendered, ink, lines, layout)
        document.state = advance(document.state, "CROPS_GENERATED")

        # → OCR_PROCESSING (line crops drive transcription; caret crops give
        # the inserted text for reconstruction)
        ocr_crops = [c for c in page.crops if c.type in ("line", "caret")]
        for i, crop in enumerate(ocr_crops, 1):
            result = run_line_crop(layout.doc_root / crop.path)
            result.cropId = crop.id
            persist_ocr(layout, page_meta.pageNumber, result)
            page.ocr.append(result)
            if on_ocr_progress is not None:
                on_ocr_progress(i, len(ocr_crops))
        document.state = advance(document.state, "OCR_PROCESSING")

        # remap caret anchors from raw segmentation ids to paragraph line ids
        if answer is not None:
            answer_lines = answer_line_regions(lines, answer)
            for caret in page.carets:
                y = caret.caret.get("bbox", {}).get("y")
                if y is None:
                    continue
                for para in answer.paragraphs:
                    para_lines = [
                        lr for lr in answer_lines
                        if para.bbox.y <= lr.bbox.y <= para.bbox.y + para.bbox.height
                    ]
                    for idx, lr in enumerate(para_lines, 1):
                        if lr.bbox.y <= y <= lr.bbox.y + lr.bbox.height + 8:
                            caret.anchorLineId = f"{para.id}_line{idx:03d}"

        # question text from its line crops (literal, uncorrected)
        if page.question is not None:
            by_crop = {o.cropId: o for o in page.ocr}
            q_lines = [
                by_crop[c.id].text
                for c in page.crops
                if c.type == "line" and c.parentId == page.question.id
            ]
            page.question.text = " ".join(q_lines)

        document.pages.append(page)

    # → MARKUP_RECONSTRUCTION
    ink_by_page = {
        p.pageNumber: _imread(
            layout.processed_page(p.pageNumber) / "ink_mask.png", cv2.IMREAD_GRAYSCALE
        )
        for p in document.pages
    }
    reconstruct_document(document, ink_by_page)
    document.state = advance(document.state, "MARKUP_RECONSTRUCTION")

    # optional LLM review (no-op unless enabled) — after reconstruction,
    # before human review (spec 39.1.7)
    words_by_line = _words_by_line_id(document, ink_by_page)
    run_llm_review(document, words_by_line_id=words_by_line)

    # → REVIEW_REQUIRED
    enter_review(document)
    if on_state_change is not None:
        on_state_change(document.state)
    return document


def finalize_document(document: Document, layout: StorageLayout) -> str:
    """APPROVED → EXPORTED; writes output/document.json. Returns rel path."""
    from .review import approve

    approve(document)
    return export_document(document, layout)


def _words_by_line_id(document: Document, ink_by_page: dict) -> dict:
    words: dict = {}
    for page in document.pages:
        ink = ink_by_page.get(page.pageNumber)
        if ink is None or page.answer is None:
            continue
        for para in page.answer.paragraphs:
            for line in para.lines:
                words[line.id] = segment_words(ink, line.bbox)
    return words
