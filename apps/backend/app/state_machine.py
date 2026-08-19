"""Document processing state machine (task 4).

Spec Section 40:

    UPLOADED → NORMALIZED → QUESTION_DETECTED → ANSWER_DETECTED →
    PARAGRAPHS_DETECTED → CROPS_GENERATED → OCR_PROCESSING →
    MARKUP_RECONSTRUCTION → REVIEW_REQUIRED → APPROVED → EXPORTED

Corrections from review loop back toward approval: corrections are accepted
while in REVIEW_REQUIRED and the document stays in REVIEW_REQUIRED until
explicitly approved.
"""

from __future__ import annotations

STATES = (
    "UPLOADED",
    "NORMALIZED",
    "QUESTION_DETECTED",
    "ANSWER_DETECTED",
    "PARAGRAPHS_DETECTED",
    "CROPS_GENERATED",
    "OCR_PROCESSING",
    "MARKUP_RECONSTRUCTION",
    "REVIEW_REQUIRED",
    "APPROVED",
    "EXPORTED",
)

# Allowed forward transitions (state → set of next states).
_TRANSITIONS: dict[str, set[str]] = {
    "UPLOADED": {"NORMALIZED"},
    "NORMALIZED": {"QUESTION_DETECTED"},
    "QUESTION_DETECTED": {"ANSWER_DETECTED"},
    "ANSWER_DETECTED": {"PARAGRAPHS_DETECTED"},
    "PARAGRAPHS_DETECTED": {"CROPS_GENERATED"},
    "CROPS_GENERATED": {"OCR_PROCESSING"},
    "OCR_PROCESSING": {"MARKUP_RECONSTRUCTION"},
    "MARKUP_RECONSTRUCTION": {"REVIEW_REQUIRED"},
    # Corrections loop inside review; approval moves forward.
    "REVIEW_REQUIRED": {"REVIEW_REQUIRED", "APPROVED"},
    "APPROVED": {"EXPORTED"},
    "EXPORTED": set(),
}


class StateTransitionError(ValueError):
    pass


def is_valid_state(state: str) -> bool:
    return state in STATES


def can_transition(current: str, next_state: str) -> bool:
    if current not in STATES or next_state not in STATES:
        return False
    return next_state in _TRANSITIONS[current]


def transition(current: str, next_state: str) -> str:
    """Advance the state machine or raise StateTransitionError."""
    if not is_valid_state(current):
        raise StateTransitionError(f"Unknown current state: {current!r}")
    if not can_transition(current, next_state):
        raise StateTransitionError(
            f"Invalid transition: {current} → {next_state} "
            f"(allowed: {sorted(_TRANSITIONS[current]) or 'none'})"
        )
    return next_state


def next_state(current: str) -> str | None:
    """The canonical forward state (None when terminal or ambiguous)."""
    options = _TRANSITIONS.get(current, set()) - {current}
    return options.pop() if len(options) == 1 else None
