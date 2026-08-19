import unittest

from app.ocr.reconstruct import reconstruct_document
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


if __name__ == "__main__":
    unittest.main()
