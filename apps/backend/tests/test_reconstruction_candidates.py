import unittest

from app.ocr.reconstruct import reconcile_paragraph_ocr, reconstruct_document
from app.schemas import (Answer, BoundingBox, Document, DocumentPage,
                         DocumentSource, OCRLine, OCRResult, PageImage, Paragraph)


class LineReconstructionTests(unittest.TestCase):
    def test_lines_join_with_spaces_tags_preserved_and_paragraphs_separated(self):
        bbox = BoundingBox(0, 0, 80, 40)
        lines = [
            OCRLine("l1", BoundingBox(0, 0, 80, 10), "l1"),
            OCRLine("l2", BoundingBox(0, 10, 80, 10), "l2"),
        ]
        paragraph = Paragraph("p1", 1, 1, bbox, "", lines=lines)
        paragraph_two = Paragraph(
            "p2",
            1,
            2,
            BoundingBox(0, 30, 80, 10),
            "",
            lines=[OCRLine("l3", BoundingBox(0, 30, 80, 10), "l3")],
        )
        page = DocumentPage(
            1,
            PageImage(1, "page.png", 80, 40, 150),
            answer=Answer(bbox, paragraphs=[paragraph, paragraph_two]),
            ocr=[
                OCRResult("l1", "The candidate felt <strikethrough>nervous</strikethrough>", .9, "mock"),
                OCRResult("l2", "<caret>very</caret> excited.", .9, "mock"),
                OCRResult("l3", "A new paragraph.", .9, "mock"),
            ],
        )
        document = Document("doc", DocumentSource("image", "source.png"), pages=[page])

        reconstructed = reconstruct_document(document)

        self.assertEqual(
            reconstructed.final.answer,
            "The candidate felt <strikethrough>nervous</strikethrough> "
            "<caret>very</caret> excited.\n\nA new paragraph.",
        )


class ParagraphReconciliationTests(unittest.TestCase):
    def _paragraph_and_ocr(self):
        lines = [OCRLine("l1", BoundingBox(0, 0, 80, 10), "l1")]
        paragraph = Paragraph("p1", 1, 1, BoundingBox(0, 0, 80, 10), "", lines=lines)
        line_result = OCRResult("l1", "The cat sat on the mat.", 0.9, "mock")
        ocr_by_crop = {"l1": line_result}
        return paragraph, line_result, ocr_by_crop

    def test_matching_paragraph_ocr_leaves_review_state_untouched(self):
        paragraph, line_result, ocr_by_crop = self._paragraph_and_ocr()
        paragraph_result = OCRResult("p1", "The cat sat on the mat.", 0.9, "mock")

        reconcile_paragraph_ocr(paragraph, "The cat sat on the mat.", paragraph_result, ocr_by_crop)

        self.assertEqual(line_result.reviewState, "pending")
        self.assertIsNone(line_result.reviewRequiredReason)

    def test_mismatched_paragraph_ocr_escalates_pending_line(self):
        paragraph, line_result, ocr_by_crop = self._paragraph_and_ocr()
        paragraph_result = OCRResult("p1", "The dog ran in the park quickly today.", 0.9, "mock")

        reconcile_paragraph_ocr(paragraph, "The cat sat on the mat.", paragraph_result, ocr_by_crop)

        self.assertEqual(line_result.reviewState, "required")
        self.assertEqual(line_result.reviewRequiredReason, "line_paragraph_mismatch")

    def test_mismatch_does_not_override_a_more_specific_reason(self):
        paragraph, line_result, ocr_by_crop = self._paragraph_and_ocr()
        line_result.reviewState = "required"
        line_result.reviewRequiredReason = "model_uncertainty"
        paragraph_result = OCRResult("p1", "The dog ran in the park quickly today.", 0.9, "mock")

        reconcile_paragraph_ocr(paragraph, "The cat sat on the mat.", paragraph_result, ocr_by_crop)

        self.assertEqual(line_result.reviewRequiredReason, "model_uncertainty")

    def test_reconstruct_document_flags_paragraph_line_mismatch(self):
        bbox = BoundingBox(0, 0, 80, 10)
        lines = [OCRLine("l1", bbox, "l1")]
        paragraph = Paragraph("p1", 1, 1, bbox, "", lines=lines)
        page = DocumentPage(
            1,
            PageImage(1, "page.png", 80, 40, 150),
            answer=Answer(bbox, paragraphs=[paragraph]),
            ocr=[OCRResult("l1", "The cat sat on the mat.", 0.9, "mock")],
            paragraphOcr=[OCRResult("p1", "Completely different sentence entirely.", 0.9, "mock")],
        )
        document = Document("doc", DocumentSource("image", "source.png"), pages=[page])

        reconstruct_document(document)

        self.assertEqual(page.ocr[0].reviewState, "required")
        self.assertEqual(page.ocr[0].reviewRequiredReason, "line_paragraph_mismatch")


if __name__ == "__main__":
    unittest.main()
