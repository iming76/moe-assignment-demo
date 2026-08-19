"""Crop generator (task 12).

Spec Sections 20-22: every crop (question/answer/paragraph/line/word/
cancelled/caret) is persisted with full metadata BEFORE any OCR runs, and
crops are immutable once written (storage.write_crop enforces this).

Crops are cut from the rendered page image so every downstream model sees
the same pixels; bounding boxes stay in rendered-page coordinates.
"""

from __future__ import annotations

from datetime import datetime, timezone

import cv2
import numpy as np

from .opencv_analysis import LineRegion, segment_words
from ..schemas import BoundingBox, Crop, DocumentPage, OCRLine, Strikethrough
from ..storage import StorageLayout, write_crop


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _crop_bytes(image: np.ndarray, bbox: BoundingBox) -> bytes:
    h, w = image.shape[:2]
    x0 = max(0, bbox.x)
    y0 = max(0, bbox.y)
    x1 = min(w, bbox.x + bbox.width)
    y1 = min(h, bbox.y + bbox.height)
    sub = image[y0:y1, x0:x1]
    ok, encoded = cv2.imencode(".png", sub)
    if not ok:
        raise ValueError(f"Failed to encode crop {bbox}")
    return encoded.tobytes()


def _persist(
    layout: StorageLayout,
    page_number: int,
    crop_type: str,
    crop_id: str,
    bbox: BoundingBox,
    parent_id: str | None,
    image: np.ndarray,
    crops: list[Crop],
) -> str:
    """Write one crop and record its metadata. Returns the relative path."""
    path = write_crop(layout, page_number, crop_type, crop_id, _crop_bytes(image, bbox))
    crops.append(
        Crop(
            id=crop_id,
            type=crop_type,
            pageNumber=page_number,
            parentId=parent_id,
            path=layout.rel(path),
            bbox=bbox,
            createdAt=_now(),
        )
    )
    return layout.rel(path)


def generate_crops(
    page: DocumentPage,
    rendered: np.ndarray,
    ink: np.ndarray,
    line_regions: list[LineRegion],
    layout: StorageLayout,
) -> list[Crop]:
    """Persist all crops for one page and fill metadata on the page object.

    Mutates page: question.cropPath, answer crop, paragraph.cropPath,
    paragraph.lines (OCRLine entries with cropIds), caret.insertCrop,
    page.crops. Returns the crop metadata list.
    """
    pn = page.pageNumber
    crops: list[Crop] = []

    # question + its physical lines
    if page.question is not None:
        q = page.question
        q.cropPath = _persist(layout, pn, "question", q.id, q.bbox, None, rendered, crops)
        for idx, lr in enumerate(
            [lr for lr in line_regions
             if q.bbox.y <= lr.bbox.y + lr.bbox.height / 2 <= q.bbox.y + q.bbox.height],
            1,
        ):
            _persist(layout, pn, "line", f"{q.id}_line{idx:03d}", lr.bbox, q.id, rendered, crops)

    # answer region + paragraphs + lines + words
    if page.answer is not None:
        _persist(layout, pn, "answer", f"answer_{pn:03d}", page.answer.bbox, None, rendered, crops)
        for para in page.answer.paragraphs:
            para.cropPath = _persist(layout, pn, "paragraph", para.id, para.bbox, None, rendered, crops)
            para_lines = [
                lr for lr in line_regions
                if para.bbox.y <= lr.bbox.y + lr.bbox.height / 2 <= para.bbox.y + para.bbox.height
            ]
            for idx, lr in enumerate(para_lines, 1):
                line_id = f"{para.id}_line{idx:03d}"
                _persist(layout, pn, "line", line_id, lr.bbox, para.id, rendered, crops)
                para.lines.append(
                    OCRLine(id=line_id, bbox=lr.bbox, cropId=line_id, text="")
                )
                for widx, wb in enumerate(segment_words(ink, lr.bbox), 1):
                    _persist(layout, pn, "word", f"{line_id}_word{widx:02d}", wb, line_id, rendered, crops)

    # cancelled (strikethrough) crops
    if page.answer is not None:
        for para in page.answer.paragraphs:
            for markup in para.markups:
                if isinstance(markup, Strikethrough) and markup.bbox is not None:
                    _persist(layout, pn, "cancelled", markup.id, markup.bbox, markup.lineId, rendered, crops)

    # caret inserted-text crops
    for caret in page.carets:
        if caret.insertBbox is not None:
            caret.insertCrop = _persist(
                layout, pn, "caret", caret.id, caret.insertBbox, caret.anchorLineId, rendered, crops
            )

    page.crops = crops
    return crops
