"""Line-only OCR reconstruction.

Physical OCR lines are joined with spaces inside a paragraph. Paragraphs are
separated by blank lines. No caret or strikethrough interpretation is applied.
"""

from __future__ import annotations

from ..schemas import Document, OCRResult, Paragraph


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
        if page.question is not None:
            questions.append(page.question.text)
        if page.answer is not None:
            paragraph_texts: list[str] = []
            for paragraph in page.answer.paragraphs:
                paragraph.text = reconstruct_paragraph(paragraph, ocr_by_crop)
                if paragraph.text:
                    paragraph_texts.append(paragraph.text)
            answers.append("\n\n".join(paragraph_texts))

    document.final.question = "\n".join(questions)
    document.final.answer = "\n\n".join(text for text in answers if text)
    return document
