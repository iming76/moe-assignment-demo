"""Configuration: named constants + YAML loader (task 3).

Every magic number in the pipeline is a named constant here or an entry in
config.yaml. `load_config()` returns a typed Config; missing keys fall back
to the named defaults so the pipeline always runs with sane values.

Spec references: Section 12 (paragraph weights), Section 35 (confidence
thresholds), Section 39.1.6 (llm_review YAML shape).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Named defaults
# ---------------------------------------------------------------------------

# Paragraph boundary score weights (spec Section 12).
DEFAULT_WEIGHT_VERTICAL_GAP = 0.55
DEFAULT_WEIGHT_INDENTATION = 0.25
DEFAULT_WEIGHT_DENSITY = 0.20
DEFAULT_PARAGRAPH_GAP_MULTIPLE = 1.6

# Low-confidence rules (spec Section 35).
DEFAULT_CONFIDENCE_ACCEPT_THRESHOLD = 0.90
DEFAULT_CONFIDENCE_REVIEW_THRESHOLD = 0.70

# Caret anchor ambiguity epsilon (spec Sections 39.1.2, 39.1.6).
DEFAULT_GAP_EPSILON_PX = 8

# LLM review defaults (spec Section 39.1.6) — disabled by default.
DEFAULT_LLM_ENABLED = False
DEFAULT_LLM_MODEL = ""
DEFAULT_LLM_BATCH = True
DEFAULT_LLM_MAX_CALLS_PER_PAGE = 10
DEFAULT_LLM_CACHE = True
DEFAULT_LLM_INCLUDE_REVIEW_RECOMMENDED = False

DEFAULT_STORAGE_ROOT = "storage"

# Document ingestion (spec Section 5.1).
DEFAULT_RENDER_DPI = 150

CONFIG_PATH = Path(__file__).resolve().parent / "config.yaml"


# ---------------------------------------------------------------------------
# Typed config objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ParagraphWeights:
    vertical_gap: float = DEFAULT_WEIGHT_VERTICAL_GAP
    indentation: float = DEFAULT_WEIGHT_INDENTATION
    density: float = DEFAULT_WEIGHT_DENSITY

    def normalized(self) -> "ParagraphWeights":
        total = self.vertical_gap + self.indentation + self.density
        if total <= 0:
            return ParagraphWeights()
        return ParagraphWeights(
            vertical_gap=self.vertical_gap / total,
            indentation=self.indentation / total,
            density=self.density / total,
        )


@dataclass(frozen=True)
class ParagraphConfig:
    weights: ParagraphWeights = field(default_factory=ParagraphWeights)
    gap_multiple: float = DEFAULT_PARAGRAPH_GAP_MULTIPLE


@dataclass(frozen=True)
class ConfidenceConfig:
    accept_threshold: float = DEFAULT_CONFIDENCE_ACCEPT_THRESHOLD
    review_threshold: float = DEFAULT_CONFIDENCE_REVIEW_THRESHOLD

    def classify(self, confidence: float) -> str:
        """>= accept: accepted; >= review: review_recommended; else review_required."""
        if confidence >= self.accept_threshold:
            return "accepted"
        if confidence >= self.review_threshold:
            return "review_recommended"
        return "review_required"


@dataclass(frozen=True)
class CaretAnchorConfig:
    gap_epsilon_px: float = DEFAULT_GAP_EPSILON_PX


@dataclass(frozen=True)
class LLMTriggerLowConfidenceConfig:
    threshold: float = DEFAULT_CONFIDENCE_REVIEW_THRESHOLD
    include_review_recommended: bool = DEFAULT_LLM_INCLUDE_REVIEW_RECOMMENDED


@dataclass(frozen=True)
class LLMTriggerCaretAnchorConfig:
    gap_epsilon_px: float = DEFAULT_GAP_EPSILON_PX


@dataclass(frozen=True)
class LLMTriggersConfig:
    caret_anchor: LLMTriggerCaretAnchorConfig = field(
        default_factory=LLMTriggerCaretAnchorConfig
    )
    low_confidence: LLMTriggerLowConfidenceConfig = field(
        default_factory=LLMTriggerLowConfidenceConfig
    )


@dataclass(frozen=True)
class LLMReviewConfig:
    enabled: bool = DEFAULT_LLM_ENABLED
    model: str = DEFAULT_LLM_MODEL
    triggers: LLMTriggersConfig = field(default_factory=LLMTriggersConfig)
    batch: bool = DEFAULT_LLM_BATCH
    max_calls_per_page: int = DEFAULT_LLM_MAX_CALLS_PER_PAGE
    cache: bool = DEFAULT_LLM_CACHE


@dataclass(frozen=True)
class StorageConfig:
    root: str = DEFAULT_STORAGE_ROOT


@dataclass(frozen=True)
class IngestionConfig:
    render_dpi: int = DEFAULT_RENDER_DPI


@dataclass(frozen=True)
class Config:
    paragraph: ParagraphConfig = field(default_factory=ParagraphConfig)
    confidence: ConfidenceConfig = field(default_factory=ConfidenceConfig)
    caret_anchor: CaretAnchorConfig = field(default_factory=CaretAnchorConfig)
    llm_review: LLMReviewConfig = field(default_factory=LLMReviewConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    ingestion: IngestionConfig = field(default_factory=IngestionConfig)


# ---------------------------------------------------------------------------
# YAML loading
# ---------------------------------------------------------------------------


def _num(d: dict[str, Any], key: str, default: float) -> float:
    value = d.get(key, default)
    return float(value)


def _bool(d: dict[str, Any], key: str, default: bool) -> bool:
    value = d.get(key, default)
    return bool(value)


def _int(d: dict[str, Any], key: str, default: int) -> int:
    value = d.get(key, default)
    return int(value)


def _load_paragraph(raw: dict[str, Any]) -> ParagraphConfig:
    w = raw.get("weights", {}) or {}
    weights = ParagraphWeights(
        vertical_gap=_num(w, "vertical_gap", DEFAULT_WEIGHT_VERTICAL_GAP),
        indentation=_num(w, "indentation", DEFAULT_WEIGHT_INDENTATION),
        density=_num(w, "density", DEFAULT_WEIGHT_DENSITY),
    ).normalized()
    return ParagraphConfig(
        weights=weights,
        gap_multiple=_num(raw, "gap_multiple", DEFAULT_PARAGRAPH_GAP_MULTIPLE),
    )


def _load_confidence(raw: dict[str, Any]) -> ConfidenceConfig:
    return ConfidenceConfig(
        accept_threshold=_num(raw, "accept_threshold", DEFAULT_CONFIDENCE_ACCEPT_THRESHOLD),
        review_threshold=_num(raw, "review_threshold", DEFAULT_CONFIDENCE_REVIEW_THRESHOLD),
    )


def _load_caret_anchor(raw: dict[str, Any]) -> CaretAnchorConfig:
    return CaretAnchorConfig(
        gap_epsilon_px=_num(raw, "gap_epsilon_px", DEFAULT_GAP_EPSILON_PX)
    )


def _load_llm_review(raw: dict[str, Any]) -> LLMReviewConfig:
    triggers_raw = raw.get("triggers", {}) or {}
    caret_raw = triggers_raw.get("caret_anchor", {}) or {}
    low_raw = triggers_raw.get("low_confidence", {}) or {}
    triggers = LLMTriggersConfig(
        caret_anchor=LLMTriggerCaretAnchorConfig(
            gap_epsilon_px=_num(caret_raw, "gap_epsilon_px", DEFAULT_GAP_EPSILON_PX)
        ),
        low_confidence=LLMTriggerLowConfidenceConfig(
            threshold=_num(low_raw, "threshold", DEFAULT_CONFIDENCE_REVIEW_THRESHOLD),
            include_review_recommended=_bool(
                low_raw,
                "include_review_recommended",
                DEFAULT_LLM_INCLUDE_REVIEW_RECOMMENDED,
            ),
        ),
    )
    return LLMReviewConfig(
        enabled=_bool(raw, "enabled", DEFAULT_LLM_ENABLED),
        model=str(raw.get("model", DEFAULT_LLM_MODEL)),
        triggers=triggers,
        batch=_bool(raw, "batch", DEFAULT_LLM_BATCH),
        max_calls_per_page=_int(raw, "max_calls_per_page", DEFAULT_LLM_MAX_CALLS_PER_PAGE),
        cache=_bool(raw, "cache", DEFAULT_LLM_CACHE),
    )


def _load_storage(raw: dict[str, Any]) -> StorageConfig:
    return StorageConfig(root=str(raw.get("root", DEFAULT_STORAGE_ROOT)))


def _load_ingestion(raw: dict[str, Any]) -> IngestionConfig:
    return IngestionConfig(render_dpi=_int(raw, "render_dpi", DEFAULT_RENDER_DPI))


def load_config(path: Optional[Path] = None) -> Config:
    """Load config.yaml over the named defaults. Missing file or keys → defaults."""
    config_path = Path(path) if path is not None else CONFIG_PATH
    if not config_path.exists():
        return Config()

    try:
        import yaml
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("pyyaml is required to load config.yaml (pip install pyyaml)") from exc

    raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}

    return Config(
        paragraph=_load_paragraph(raw.get("paragraph", {}) or {}),
        confidence=_load_confidence(raw.get("confidence", {}) or {}),
        caret_anchor=_load_caret_anchor(raw.get("caret_anchor", {}) or {}),
        llm_review=_load_llm_review(raw.get("llm_review", {}) or {}),
        storage=_load_storage(raw.get("storage", {}) or {}),
        ingestion=_load_ingestion(raw.get("ingestion", {}) or {}),
    )


# Module-level default config — import this for quick access:
#   from config import CONFIG
CONFIG = load_config()
