"""Shared data schemas for the handwritten-script-ocr pipeline.

Single source of truth for all pipeline data structures. Mirrored 1:1 by
packages/types/src/index.ts — any shape change must land in both.

Plain dataclasses with camelCase JSON keys (per spec Sections 5.1, 9, 14,
17, 19, 22, 24, 31, 39.1.4). Helpers: to_json / from_json on every schema.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Geometry / normalization
# ---------------------------------------------------------------------------


@dataclass
class BoundingBox:
    x: int
    y: int
    width: int
    height: int

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_json(d: dict[str, Any]) -> "BoundingBox":
        return BoundingBox(x=d["x"], y=d["y"], width=d["width"], height=d["height"])


@dataclass
class Point:
    x: int
    y: int

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_json(d: dict[str, Any]) -> "Point":
        return Point(x=d["x"], y=d["y"])


@dataclass
class PageImage:
    """Normalized page representation (spec Section 5.1)."""

    pageNumber: int
    path: str
    width: int
    height: int
    dpi: int

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_json(d: dict[str, Any]) -> "PageImage":
        return PageImage(
            pageNumber=d["pageNumber"],
            path=d["path"],
            width=d["width"],
            height=d["height"],
            dpi=d["dpi"],
        )


# ---------------------------------------------------------------------------
# Spatial detections
# ---------------------------------------------------------------------------


@dataclass
class Question:
    """Spec Section 9."""

    id: str
    bbox: BoundingBox
    cropPath: str
    lines: list[str] = field(default_factory=list)
    text: str = ""
    confidence: Optional[float] = None

    def to_json(self) -> dict[str, Any]:
        d = {
            "id": self.id,
            "bbox": self.bbox.to_json(),
            "cropPath": self.cropPath,
            "lines": list(self.lines),
            "text": self.text,
        }
        if self.confidence is not None:
            d["confidence"] = self.confidence
        return d

    @staticmethod
    def from_json(d: dict[str, Any]) -> "Question":
        return Question(
            id=d["id"],
            bbox=BoundingBox.from_json(d["bbox"]),
            cropPath=d["cropPath"],
            lines=list(d.get("lines", [])),
            text=d.get("text", ""),
            confidence=d.get("confidence"),
        )


@dataclass
class OCRToken:
    """Optional token-level detail on an OCRResult."""

    text: str
    confidence: float

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_json(d: dict[str, Any]) -> "OCRToken":
        return OCRToken(text=d["text"], confidence=d["confidence"])


@dataclass
class OCRLine:
    """One physical handwriting line inside a paragraph (spec Section 14)."""

    id: str
    bbox: BoundingBox
    cropId: str
    text: str = ""
    confidence: Optional[float] = None

    def to_json(self) -> dict[str, Any]:
        d = {
            "id": self.id,
            "bbox": self.bbox.to_json(),
            "cropId": self.cropId,
            "text": self.text,
        }
        if self.confidence is not None:
            d["confidence"] = self.confidence
        return d

    @staticmethod
    def from_json(d: dict[str, Any]) -> "OCRLine":
        return OCRLine(
            id=d["id"],
            bbox=BoundingBox.from_json(d["bbox"]),
            cropId=d["cropId"],
            text=d.get("text", ""),
            confidence=d.get("confidence"),
        )


# ---------------------------------------------------------------------------
# Markup
# ---------------------------------------------------------------------------


@dataclass
class Highlight:
    """Spec Section 17."""

    id: str
    type: str = "highlight"
    bbox: Optional[BoundingBox] = None
    polygon: list[Point] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        d: dict[str, Any] = {"id": self.id, "type": self.type}
        if self.bbox is not None:
            d["bbox"] = self.bbox.to_json()
        if self.polygon:
            d["polygon"] = [p.to_json() for p in self.polygon]
        return d

    @staticmethod
    def from_json(d: dict[str, Any]) -> "Highlight":
        return Highlight(
            id=d["id"],
            type=d.get("type", "highlight"),
            bbox=BoundingBox.from_json(d["bbox"]) if d.get("bbox") else None,
            polygon=[Point.from_json(p) for p in d.get("polygon", [])],
        )


@dataclass
class Strikethrough:
    """Spec Section 18 — cancelled text region."""

    id: str
    type: str = "strikethrough"
    bbox: Optional[BoundingBox] = None
    cropPath: Optional[str] = None
    strokeBbox: Optional[BoundingBox] = None
    lineId: Optional[str] = None

    def to_json(self) -> dict[str, Any]:
        d: dict[str, Any] = {"id": self.id, "type": self.type}
        if self.bbox is not None:
            d["bbox"] = self.bbox.to_json()
        if self.cropPath is not None:
            d["cropPath"] = self.cropPath
        if self.strokeBbox is not None:
            d["strokeBbox"] = self.strokeBbox.to_json()
        if self.lineId is not None:
            d["lineId"] = self.lineId
        return d

    @staticmethod
    def from_json(d: dict[str, Any]) -> "Strikethrough":
        return Strikethrough(
            id=d["id"],
            type=d.get("type", "strikethrough"),
            bbox=BoundingBox.from_json(d["bbox"]) if d.get("bbox") else None,
            cropPath=d.get("cropPath"),
            strokeBbox=BoundingBox.from_json(d["strokeBbox"]) if d.get("strokeBbox") else None,
            lineId=d.get("lineId"),
        )


@dataclass
class LLMReview:
    """Spec Section 39.1.4 — applied stays false until a human confirms."""

    id: str
    targetId: str
    trigger: str  # "caret_anchor_ambiguity" | "low_confidence"
    inputs: dict[str, Any] = field(default_factory=dict)  # cropPaths, candidates
    rawResponse: Optional[dict[str, Any]] = None
    chosen: Any = None  # candidate / anchor index chosen
    agreedWithDeterministic: bool = False
    applied: bool = False
    model: str = ""
    latencyMs: int = 0

    def to_json(self) -> dict[str, Any]:
        d = {
            "id": self.id,
            "targetId": self.targetId,
            "trigger": self.trigger,
            "inputs": dict(self.inputs),
            "rawResponse": self.rawResponse,
            "chosen": self.chosen,
            "agreedWithDeterministic": self.agreedWithDeterministic,
            "applied": self.applied,
            "model": self.model,
            "latencyMs": self.latencyMs,
        }
        return d

    @staticmethod
    def from_json(d: dict[str, Any]) -> "LLMReview":
        return LLMReview(
            id=d["id"],
            targetId=d["targetId"],
            trigger=d["trigger"],
            inputs=dict(d.get("inputs", {})),
            rawResponse=d.get("rawResponse"),
            chosen=d.get("chosen"),
            agreedWithDeterministic=d.get("agreedWithDeterministic", False),
            applied=d.get("applied", False),
            model=d.get("model", ""),
            latencyMs=d.get("latencyMs", 0),
        )


@dataclass
class Caret:
    """Spec Section 19 — caret insertion markup."""

    id: str
    type: str = "caret"
    caret: dict[str, Any] = field(default_factory=dict)  # {"bbox": {...}}
    insertCrop: str = ""
    anchorLineId: str = ""
    insertBbox: Optional[BoundingBox] = None
    anchorCandidates: list[int] = field(default_factory=list)
    llmReview: Optional[LLMReview] = None

    def to_json(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "id": self.id,
            "type": self.type,
            "caret": dict(self.caret),
            "insertCrop": self.insertCrop,
            "anchorLineId": self.anchorLineId,
        }
        if self.insertBbox is not None:
            d["insertBbox"] = self.insertBbox.to_json()
        if self.anchorCandidates:
            d["anchorCandidates"] = list(self.anchorCandidates)
        if self.llmReview is not None:
            d["llmReview"] = self.llmReview.to_json()
        return d

    @staticmethod
    def from_json(d: dict[str, Any]) -> "Caret":
        return Caret(
            id=d["id"],
            type=d.get("type", "caret"),
            caret=dict(d.get("caret", {})),
            insertCrop=d.get("insertCrop", ""),
            anchorLineId=d.get("anchorLineId", ""),
            insertBbox=BoundingBox.from_json(d["insertBbox"]) if d.get("insertBbox") else None,
            anchorCandidates=list(d.get("anchorCandidates", [])),
            llmReview=LLMReview.from_json(d["llmReview"]) if d.get("llmReview") else None,
        )


# Markup union for Paragraph.markups
Markup = Strikethrough | Caret

MARKUP_TYPES = {"strikethrough": Strikethrough, "caret": Caret}


def markup_from_json(d: dict[str, Any]) -> Markup:
    cls = MARKUP_TYPES.get(d.get("type", ""))
    if cls is None:
        raise ValueError(f"Unknown markup type: {d.get('type')!r}")
    return cls.from_json(d)


# ---------------------------------------------------------------------------
# Crops & OCR
# ---------------------------------------------------------------------------

CROP_TYPES = (
    "question",
    "answer",
    "paragraph",
    "line",
    "word",
    "cancelled",
    "caret",
)


@dataclass
class Crop:
    """Spec Section 22 — immutable once written."""

    id: str
    type: str
    pageNumber: int
    path: str
    bbox: BoundingBox
    createdAt: str
    parentId: Optional[str] = None

    def to_json(self) -> dict[str, Any]:
        d = {
            "id": self.id,
            "type": self.type,
            "pageNumber": self.pageNumber,
            "path": self.path,
            "bbox": self.bbox.to_json(),
            "createdAt": self.createdAt,
        }
        if self.parentId is not None:
            d["parentId"] = self.parentId
        return d

    @staticmethod
    def from_json(d: dict[str, Any]) -> "Crop":
        return Crop(
            id=d["id"],
            type=d["type"],
            pageNumber=d["pageNumber"],
            path=d["path"],
            bbox=BoundingBox.from_json(d["bbox"]),
            createdAt=d["createdAt"],
            parentId=d.get("parentId"),
        )


@dataclass
class OCRResult:
    """Spec Section 24 — literal text only, never corrected."""

    cropId: str
    text: str
    confidence: float
    model: str
    tokens: list[OCRToken] = field(default_factory=list)
    candidates: list[dict[str, Any]] = field(default_factory=list)  # N-best: [{"text","confidence"}]
    processingTimeMs: Optional[int] = None
    llmReview: Optional[LLMReview] = None

    def to_json(self) -> dict[str, Any]:
        d = {
            "cropId": self.cropId,
            "text": self.text,
            "confidence": self.confidence,
            "model": self.model,
        }
        if self.tokens:
            d["tokens"] = [t.to_json() for t in self.tokens]
        if self.candidates:
            d["candidates"] = list(self.candidates)
        if self.processingTimeMs is not None:
            d["processingTimeMs"] = self.processingTimeMs
        if self.llmReview is not None:
            d["llmReview"] = self.llmReview.to_json()
        return d

    @staticmethod
    def from_json(d: dict[str, Any]) -> "OCRResult":
        return OCRResult(
            cropId=d["cropId"],
            text=d["text"],
            confidence=d["confidence"],
            model=d["model"],
            tokens=[OCRToken.from_json(t) for t in d.get("tokens", [])],
            candidates=list(d.get("candidates", [])),
            processingTimeMs=d.get("processingTimeMs"),
            llmReview=LLMReview.from_json(d["llmReview"]) if d.get("llmReview") else None,
        )


# ---------------------------------------------------------------------------
# Document assembly
# ---------------------------------------------------------------------------


@dataclass
class Paragraph:
    """Spec Section 14."""

    id: str
    pageNumber: int
    order: int
    bbox: BoundingBox
    cropPath: str
    lines: list[OCRLine] = field(default_factory=list)
    highlights: list[Highlight] = field(default_factory=list)
    markups: list[Markup] = field(default_factory=list)
    text: str = ""

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "pageNumber": self.pageNumber,
            "order": self.order,
            "bbox": self.bbox.to_json(),
            "cropPath": self.cropPath,
            "lines": [ln.to_json() for ln in self.lines],
            "highlights": [h.to_json() for h in self.highlights],
            "markups": [m.to_json() for m in self.markups],
            "text": self.text,
        }

    @staticmethod
    def from_json(d: dict[str, Any]) -> "Paragraph":
        return Paragraph(
            id=d["id"],
            pageNumber=d["pageNumber"],
            order=d["order"],
            bbox=BoundingBox.from_json(d["bbox"]),
            cropPath=d["cropPath"],
            lines=[OCRLine.from_json(ln) for ln in d.get("lines", [])],
            highlights=[Highlight.from_json(h) for h in d.get("highlights", [])],
            markups=[markup_from_json(m) for m in d.get("markups", [])],
            text=d.get("text", ""),
        )


@dataclass
class Answer:
    """Answer region: bbox + paragraphs (spec Sections 10, 31)."""

    bbox: BoundingBox
    cropPath: str = ""
    paragraphs: list[Paragraph] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        d = {
            "bbox": self.bbox.to_json(),
            "paragraphs": [p.to_json() for p in self.paragraphs],
        }
        if self.cropPath:
            d["cropPath"] = self.cropPath
        return d

    @staticmethod
    def from_json(d: dict[str, Any]) -> "Answer":
        return Answer(
            bbox=BoundingBox.from_json(d["bbox"]),
            cropPath=d.get("cropPath", ""),
            paragraphs=[Paragraph.from_json(p) for p in d.get("paragraphs", [])],
        )


@dataclass
class DocumentPage:
    """One page of the internal document JSON (spec Section 31)."""

    pageNumber: int
    image: PageImage
    question: Optional[Question] = None
    answer: Optional[Answer] = None
    highlights: list[Highlight] = field(default_factory=list)
    carets: list[Caret] = field(default_factory=list)
    crops: list[Crop] = field(default_factory=list)
    ocr: list[OCRResult] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "pageNumber": self.pageNumber,
            "image": self.image.to_json(),
        }
        if self.question is not None:
            d["question"] = self.question.to_json()
        if self.answer is not None:
            d["answer"] = self.answer.to_json()
        d["highlights"] = [h.to_json() for h in self.highlights]
        d["carets"] = [c.to_json() for c in self.carets]
        d["crops"] = [c.to_json() for c in self.crops]
        d["ocr"] = [o.to_json() for o in self.ocr]
        return d

    @staticmethod
    def from_json(d: dict[str, Any]) -> "DocumentPage":
        return DocumentPage(
            pageNumber=d["pageNumber"],
            image=PageImage.from_json(d["image"]),
            question=Question.from_json(d["question"]) if d.get("question") else None,
            answer=Answer.from_json(d["answer"]) if d.get("answer") else None,
            highlights=[Highlight.from_json(h) for h in d.get("highlights", [])],
            carets=[Caret.from_json(c) for c in d.get("carets", [])],
            crops=[Crop.from_json(c) for c in d.get("crops", [])],
            ocr=[OCRResult.from_json(o) for o in d.get("ocr", [])],
        )


@dataclass
class DocumentSource:
    type: str  # "image" | "pdf"
    originalPath: str

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_json(d: dict[str, Any]) -> "DocumentSource":
        return DocumentSource(type=d["type"], originalPath=d["originalPath"])


@dataclass
class FinalOutput:
    """Spec Section 30 — question + answer with \n\n between paragraphs."""

    question: str = ""
    answer: str = ""

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_json(d: dict[str, Any]) -> "FinalOutput":
        return FinalOutput(question=d.get("question", ""), answer=d.get("answer", ""))


@dataclass
class ReviewCorrection:
    """Human review correction (spec Section 34)."""

    id: str
    cropId: str
    originalText: str
    correctedText: str
    reason: str = ""
    createdAt: str = ""

    def to_json(self) -> dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_json(d: dict[str, Any]) -> "ReviewCorrection":
        return ReviewCorrection(
            id=d["id"],
            cropId=d["cropId"],
            originalText=d["originalText"],
            correctedText=d["correctedText"],
            reason=d.get("reason", ""),
            createdAt=d.get("createdAt", ""),
        )


@dataclass
class Document:
    """Complete internal JSON (spec Section 31)."""

    documentId: str
    source: DocumentSource
    state: str = "UPLOADED"
    pages: list[DocumentPage] = field(default_factory=list)
    final: FinalOutput = field(default_factory=FinalOutput)
    corrections: list[ReviewCorrection] = field(default_factory=list)
    llmReviews: list[LLMReview] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {
            "documentId": self.documentId,
            "source": self.source.to_json(),
            "state": self.state,
            "pages": [p.to_json() for p in self.pages],
            "final": self.final.to_json(),
            "corrections": [c.to_json() for c in self.corrections],
            "llmReviews": [r.to_json() for r in self.llmReviews],
        }

    @staticmethod
    def from_json(d: dict[str, Any]) -> "Document":
        return Document(
            documentId=d["documentId"],
            source=DocumentSource.from_json(d["source"]),
            state=d.get("state", "UPLOADED"),
            pages=[DocumentPage.from_json(p) for p in d.get("pages", [])],
            final=FinalOutput.from_json(d.get("final", {})),
            corrections=[ReviewCorrection.from_json(c) for c in d.get("corrections", [])],
            llmReviews=[LLMReview.from_json(r) for r in d.get("llmReviews", [])],
        )


def dump_json(obj: Any) -> str:
    """Serialize any schema object (or list of them) to indented JSON."""
    if isinstance(obj, list):
        return json.dumps([o.to_json() for o in obj], indent=2, ensure_ascii=False)
    return json.dumps(obj.to_json(), indent=2, ensure_ascii=False)
