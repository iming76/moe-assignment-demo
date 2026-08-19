from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import cv2

from .config import CONFIG
from .imaging.crop_generator import generate_crops
from .detect.answers import answer_line_regions, detect_answer
from .detect.highlights import detect_highlights
from .detect.paragraphs import detect_paragraphs
from .detect.questions import detect_questions
from .imaging.normalize_image import preprocess_page
from .imaging.opencv_analysis import (
    ruled_line_bands,
    segment_lines,
)
from .ingest.pages import ingest_document
from .ocr.reconstruct import reconstruct_document
from .review import enter_review, export_document
from .ocr.vision_llm import VisionLLMClient, persist_ocr
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
    vision = VisionLLMClient(CONFIG.vision_llm, cache_dir=layout.doc_root / "ocr" / "vision_cache")

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
        cv2.imwrite(
            str(layout.processed_page(page_meta.pageNumber) / "highlight_mask.png"),
            hmask,
        )
        page.highlights = highlights

        ink = _imread(
            layout.processed_page(page_meta.pageNumber) / "ink_mask.png",
            cv2.IMREAD_GRAYSCALE,
        )

        # NORMALIZED → QUESTION_DETECTED
        lines = segment_lines(ink)
        rule_bands = ruled_line_bands(ink)
        questions = detect_questions(lines, page_meta.pageNumber, rule_bands=rule_bands)
        if document.state == "NORMALIZED":
            document.state = advance(document.state, "QUESTION_DETECTED")
        page.question = questions[0] if questions else None

        # → ANSWER_DETECTED
        answer = detect_answer(lines, questions, page_meta.pageNumber, ink)
        if document.state == "QUESTION_DETECTED":
            document.state = advance(document.state, "ANSWER_DETECTED")
        page.answer = answer

        # → PARAGRAPHS_DETECTED
        if answer is not None:
            answer.paragraphs = detect_paragraphs(
                answer_line_regions(lines, answer),
                ink,
                page_meta.pageNumber,
                answer.bbox,
            )
        if document.state == "ANSWER_DETECTED":
            document.state = advance(document.state, "PARAGRAPHS_DETECTED")

        # → CROPS_GENERATED (all crops persisted BEFORE any OCR)
        generate_crops(page, rendered, ink, lines, layout, rule_bands)
        if document.state == "PARAGRAPHS_DETECTED":
            document.state = advance(document.state, "CROPS_GENERATED")

        # → OCR_PROCESSING: only immutable line crops are model inputs.
        ocr_crops = [c for c in page.crops if c.type == "line"]
        for i, crop in enumerate(ocr_crops, 1):
            crop_path = layout.doc_root / crop.path
            result = vision.transcribe_line(crop_path, crop.id, page_meta.pageNumber)
            result.cropId = crop.id
            persist_ocr(layout, page_meta.pageNumber, result)
            page.ocr.append(result)
            if on_ocr_progress is not None:
                on_ocr_progress(i, len(ocr_crops))
        if document.state == "CROPS_GENERATED":
            document.state = advance(document.state, "OCR_PROCESSING")

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
    reconstruct_document(document)
    document.state = advance(document.state, "MARKUP_RECONSTRUCTION")

    # → REVIEW_REQUIRED
    enter_review(document)
    if on_state_change is not None:
        on_state_change(document.state)
    return document


def finalize_document(document: Document, layout: StorageLayout) -> str:
    """APPROVED → EXPORTED; writes output/document.json. Returns rel path."""
    from .review import apply_corrections, approve

    apply_corrections(document)
    reconstruct_document(document)
    approve(document)
    return export_document(document, layout)
