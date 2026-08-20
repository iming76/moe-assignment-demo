"""Human review flow (task 15).

Spec Section 34 + human-review capability: after reconstruction the document
enters REVIEW_REQUIRED; low-confidence lines are flagged with configurable
thresholds (>= 0.90 accepted, 0.70-0.89 review recommended, < 0.70 review
required).
"""

from __future__ import annotations

from .config import CONFIG
from .schemas import Document
from .state_machine import transition


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
