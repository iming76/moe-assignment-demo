"""Human review flow (task 15).

Spec Section 34 + human-review capability: after reconstruction the document
enters REVIEW_REQUIRED; low-confidence lines are flagged with configurable
thresholds (>= 0.90 accepted, 0.70-0.89 review recommended, < 0.70 review
required); manual corrections are recorded; approval moves the state machine
to APPROVED and export writes the final JSON (EXPORTED).
"""

from __future__ import annotations

from datetime import datetime, timezone

from config import CONFIG
from schemas import Document, ReviewCorrection
from state_machine import transition
from storage import StorageLayout


def classify(confidence: float) -> str:
    return CONFIG.confidence.classify(confidence)


def flag_low_confidence(document: Document) -> dict[str, list[str]]:
    """Return {"review_required": [cropIds], "review_recommended": [cropIds]}."""
    required: list[str] = []
    recommended: list[str] = []
    for page in document.pages:
        for result in page.ocr:
            kind = classify(result.confidence)
            if kind == "review_required":
                required.append(result.cropId)
            elif kind == "review_recommended":
                recommended.append(result.cropId)
    return {"review_required": required, "review_recommended": recommended}


def enter_review(document: Document) -> Document:
    """Move MARKUP_RECONSTRUCTION → REVIEW_REQUIRED."""
    document.state = transition(document.state, "REVIEW_REQUIRED")
    return document


def submit_correction(
    document: Document,
    crop_id: str,
    corrected_text: str,
    reason: str = "",
) -> ReviewCorrection:
    """Record a manual correction while in REVIEW_REQUIRED."""
    if document.state != "REVIEW_REQUIRED":
        raise ValueError(f"Corrections are only accepted in REVIEW_REQUIRED, not {document.state}")
    original = ""
    for page in document.pages:
        for result in page.ocr:
            if result.cropId == crop_id:
                original = result.text
    correction = ReviewCorrection(
        id=f"corr_{len(document.corrections) + 1:03d}",
        cropId=crop_id,
        originalText=original,
        correctedText=corrected_text,
        reason=reason,
        createdAt=datetime.now(timezone.utc).isoformat(),
    )
    document.corrections.append(correction)
    return correction


def apply_corrections(document: Document) -> Document:
    """Rebuild paragraph/final text with corrections substituted."""
    corrected = {c.cropId: c.correctedText for c in document.corrections}
    for page in document.pages:
        for result in page.ocr:
            if result.cropId in corrected:
                result.text = corrected[result.cropId]
    return document


def approve(document: Document) -> Document:
    document.state = transition(document.state, "APPROVED")
    return document


def export_document(document: Document, layout: StorageLayout) -> str:
    """Write output/document.json and advance to EXPORTED. Returns rel path."""
    import json

    document.state = transition(document.state, "EXPORTED")
    path = layout.output_json_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document.to_json(), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return layout.rel(path)
