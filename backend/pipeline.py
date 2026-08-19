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

import cv2

from config import CONFIG
from crop_generator import generate_crops
from detect_answers import answer_line_regions, detect_answer
from detect_carets import detect_carets
from detect_highlights import detect_highlights
from detect_paragraphs import detect_paragraphs
from detect_questions import detect_questions
from detect_strikethroughs import detect_strikethroughs
from llm_review import run_llm_review
from normalize_image import preprocess_page
from opencv_analysis import median_line_height, segment_lines, segment_words
from pdf_to_pages import ingest_document
from reconstruct import reconstruct_document
from review import enter_review, export_document
from run_trocr import persist_ocr, run_line_crop
from schemas import Document
from state_machine import transition
from storage import StorageLayout


def _imread(path: Path, flags: int = cv2.IMREAD_COLOR):
    image = cv2.imread(str(path), flags)
    if image is None:
        raise FileNotFoundError(f"Image not found: {path}")
    return image


def process_document(source_path: Path, document_id: str, root: str | None = None) -> Document:
    """Run the full pipeline to REVIEW_REQUIRED and return the document."""
    layout = StorageLayout(document_id, root=root)

    # UPLOADED → NORMALIZED
    source, pages_meta = ingest_document(source_path, layout)
    document = Document(documentId=document_id, source=source, state="UPLOADED")
    document.state = transition(document.state, "NORMALIZED")

    for page_meta in pages_meta:
        from schemas import DocumentPage

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
        document.state = transition(document.state, "QUESTION_DETECTED")
        page.question = questions[0] if questions else None

        # → ANSWER_DETECTED
        answer = detect_answer(lines, questions, page_meta.pageNumber, ink)
        document.state = transition(document.state, "ANSWER_DETECTED")
        page.answer = answer

        # → PARAGRAPHS_DETECTED
        if answer is not None:
            answer.paragraphs = detect_paragraphs(
                answer_line_regions(lines, answer), ink, page_meta.pageNumber, answer.bbox
            )
        document.state = transition(document.state, "PARAGRAPHS_DETECTED")

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
        document.state = transition(document.state, "CROPS_GENERATED")

        # → OCR_PROCESSING (line crops drive transcription; caret crops give
        # the inserted text for reconstruction)
        for crop in page.crops:
            if crop.type in ("line", "caret"):
                result = run_line_crop(layout.doc_root / crop.path)
                result.cropId = crop.id
                persist_ocr(layout, page_meta.pageNumber, result)
                page.ocr.append(result)
        document.state = transition(document.state, "OCR_PROCESSING")

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
    document.state = transition(document.state, "MARKUP_RECONSTRUCTION")

    # optional LLM review (no-op unless enabled) — after reconstruction,
    # before human review (spec 39.1.7)
    words_by_line = _words_by_line_id(document, ink_by_page)
    run_llm_review(document, words_by_line_id=words_by_line)

    # → REVIEW_REQUIRED
    enter_review(document)
    return document


def finalize_document(document: Document, layout: StorageLayout) -> str:
    """APPROVED → EXPORTED; writes output/document.json. Returns rel path."""
    from review import approve

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
