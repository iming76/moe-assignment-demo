from tempfile import TemporaryDirectory
import unittest

import numpy as np

from app.imaging.crop_generator import generate_crops
from app.imaging.opencv_analysis import LineRegion
from app.schemas import Answer, BoundingBox, DocumentPage, PageImage, Paragraph
from app.storage import StorageLayout


class LineCropTests(unittest.TestCase):
    def test_line_crop_is_persisted_and_reused_without_correction_crops(self):
        rendered = np.full((100, 160, 3), 255, dtype=np.uint8)
        ink = np.zeros((100, 160), dtype=np.uint8)
        ink[45:50, 20:45] = 255
        ink[45:50, 60:90] = 255
        bbox = BoundingBox(10, 35, 130, 30)
        para = Paragraph("p1", 1, 1, bbox, "")
        page = DocumentPage(1, PageImage(1, "rendered/page_001.png", 160, 100, 150), answer=Answer(bbox, paragraphs=[para]))
        line = LineRegion(bbox=bbox, ink_area=100)
        with TemporaryDirectory() as tmp:
            layout = StorageLayout("doc", tmp)
            crops = generate_crops(page, rendered, ink, [line], layout)
            line_crop = next(c for c in crops if c.type == "line")
            line_path = layout.doc_root / line_crop.path
            original_bytes = line_path.read_bytes()
            # A new run with the same stable IDs reuses immutable evidence.
            para2 = Paragraph("p1", 1, 1, bbox, "")
            page2 = DocumentPage(1, page.image, answer=Answer(bbox, paragraphs=[para2]))
            generate_crops(page2, rendered, ink, [line], layout)
            self.assertEqual(line_path.read_bytes(), original_bytes)
        self.assertEqual(line_crop.parentId, "p1")
        self.assertGreaterEqual(line_crop.bbox.x, 0)
        self.assertLessEqual(line_crop.bbox.x + line_crop.bbox.width, rendered.shape[1])
        self.assertFalse({"cancelled", "caret", "correction"} & {c.type for c in crops})


if __name__ == "__main__":
    unittest.main()
