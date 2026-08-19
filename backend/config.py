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
DEFAULT_PARAGRAPH_THRESHOLD = 0.5   # weighted score at which a boundary is emitted

# Highlight detection (spec Section 17) — yellow HSV window.
DEFAULT_HIGHLIGHT_HUE_MIN = 18
DEFAULT_HIGHLIGHT_HUE_MAX = 40
DEFAULT_HIGHLIGHT_SAT_MIN = 60
DEFAULT_HIGHLIGHT_SAT_MAX = 255
DEFAULT_HIGHLIGHT_VAL_MIN = 120
DEFAULT_HIGHLIGHT_VAL_MAX = 255
DEFAULT_HIGHLIGHT_CLEANUP_SIZE = 5
DEFAULT_HIGHLIGHT_MIN_AREA = 400


@dataclass(frozen=True)
class HighlightConfig:
    hue_min: int = DEFAULT_HIGHLIGHT_HUE_MIN
    hue_max: int = DEFAULT_HIGHLIGHT_HUE_MAX
    sat_min: int = DEFAULT_HIGHLIGHT_SAT_MIN
    sat_max: int = DEFAULT_HIGHLIGHT_SAT_MAX
    val_min: int = DEFAULT_HIGHLIGHT_VAL_MIN
    val_max: int = DEFAULT_HIGHLIGHT_VAL_MAX
    cleanup_size: int = DEFAULT_HIGHLIGHT_CLEANUP_SIZE
    min_area: int = DEFAULT_HIGHLIGHT_MIN_AREA


# Caret detection (spec Section 19).
DEFAULT_CARET_SYMBOL_MIN = 5          # px; caret symbol component size window
DEFAULT_CARET_SYMBOL_MAX = 35
DEFAULT_CARET_SYMBOL_MIN_AREA = 20
DEFAULT_CARET_SYMBOL_MAX_AREA = 600
DEFAULT_CARET_SYMBOL_BOTTOM_FRAC = 0.0   # symbols vary (top or bottom of band)
DEFAULT_CARET_SYMBOL_BELOW_SLACK = 8     # px the symbol may dip below the band
DEFAULT_CARET_INSERT_ABOVE = 60          # inserted text floats within this above the symbol
DEFAULT_CARET_INSERT_MIN_ABOVE = 10      # inserted text starts at least this far above the symbol
DEFAULT_CARET_INSERT_MAX_DX = 60         # horizontal window around the symbol
DEFAULT_CARET_INSERT_MAX_WIDTH = 120     # inserted text is short (1-2 words)
DEFAULT_CARET_INSERT_MAX_HEIGHT = 70     # two-row insertions ("in\nlife") allowed


@dataclass(frozen=True)
class CaretConfig:
    symbol_min: int = DEFAULT_CARET_SYMBOL_MIN
    symbol_max: int = DEFAULT_CARET_SYMBOL_MAX
    symbol_min_area: int = DEFAULT_CARET_SYMBOL_MIN_AREA
    symbol_max_area: int = DEFAULT_CARET_SYMBOL_MAX_AREA
    symbol_bottom_frac: float = DEFAULT_CARET_SYMBOL_BOTTOM_FRAC
    symbol_below_slack: int = DEFAULT_CARET_SYMBOL_BELOW_SLACK
    insert_above: int = DEFAULT_CARET_INSERT_ABOVE
    insert_min_above: int = DEFAULT_CARET_INSERT_MIN_ABOVE
    insert_max_dx: int = DEFAULT_CARET_INSERT_MAX_DX
    insert_max_width: int = DEFAULT_CARET_INSERT_MAX_WIDTH
    insert_max_height: int = DEFAULT_CARET_INSERT_MAX_HEIGHT


# Strikethrough detection (spec Section 18).
DEFAULT_STRIKE_OPEN_KERNEL = 25     # horizontal open: keeps long horizontal runs
DEFAULT_STRIKE_MIN_STROKE_LEN = 80  # px; longer than any word
DEFAULT_STRIKE_MAX_THICKNESS = 20   # px; joined multi-pass strikes stay thin
DEFAULT_STRIKE_JOIN_GAP = 40        # px horizontal gap joined across fragments
DEFAULT_STRIKE_JOIN_HEIGHT = 9      # px vertical gap joined (diagonal strokes)
DEFAULT_STRIKE_MIN_ASPECT = 3       # width/height ratio for near-horizontal strokes
DEFAULT_STRIKE_MIN_CROSSED_GAP = 6  # stroke must cross inter-word space


@dataclass(frozen=True)
class StrikethroughConfig:
    open_kernel: int = DEFAULT_STRIKE_OPEN_KERNEL
    min_stroke_len: int = DEFAULT_STRIKE_MIN_STROKE_LEN
    max_stroke_thickness: int = DEFAULT_STRIKE_MAX_THICKNESS
    join_gap: int = DEFAULT_STRIKE_JOIN_GAP
    join_height: int = DEFAULT_STRIKE_JOIN_HEIGHT
    min_aspect: int = DEFAULT_STRIKE_MIN_ASPECT
    min_crossed_gap: int = DEFAULT_STRIKE_MIN_CROSSED_GAP


# Answer region detection (spec Section 10).
DEFAULT_ANSWER_TRIM_DENSITY_RATIO = 0.25  # edge lines below this * median density are specks
DEFAULT_ANSWER_MARGIN_SCRIBBLE_PX = 60    # lines starting this far left of the margin
DEFAULT_ANSWER_MIN_INK_AREA = 800         # ...with less ink than this = margin scribble
DEFAULT_HEADER_HEIGHT_FACTOR = 4.0   # lines taller than this * median = header block
DEFAULT_QUESTION_GROUP_MAX_GAP = 45  # px between question lines that still group
DEFAULT_QUESTION_SHORT_LINE_RATIO = 0.7  # continuation lines are shorter than this

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

# Image preprocessing pipeline (spec Section 16).
DEFAULT_DENOISE_H = 10
DEFAULT_CLAHE_CLIP_LIMIT = 2.0
DEFAULT_CLAHE_GRID = 8
DEFAULT_MAX_DESKEW_DEG = 15.0
DEFAULT_ADAPTIVE_BLOCK_SIZE = 31
DEFAULT_ADAPTIVE_C = 15
DEFAULT_MORPH_CLOSE_SIZE = 3
DEFAULT_MORPH_OPEN_SIZE = 2

# Line/word segmentation (spec Sections 15, 11).
DEFAULT_RULE_KERNEL_WIDTH = 60  # horizontal open kernel; rules are the only long runs
DEFAULT_MARGIN_KERNEL_HEIGHT = 60  # vertical open kernel; margin lines are long verticals
DEFAULT_RULE_ROW_WIDTH_RATIO = 0.6   # (legacy, unused by morph removal)
DEFAULT_RULE_MAX_THICKNESS = 6       # px; rules thicker than this are kept as ink
DEFAULT_LINE_GAP_TOLERANCE = 4       # blank rows allowed inside one line
DEFAULT_MIN_ROW_INK = 12             # rows below this are valleys/gaps, not ink
DEFAULT_MIN_LINE_INK_AREA = 150
DEFAULT_WORD_GAP_TOLERANCE = 3       # blank cols allowed inside one word
DEFAULT_MIN_COL_INK = 3              # cols below this are inter-word valleys
DEFAULT_MIN_WORD_WIDTH = 4
DEFAULT_PAGE_CROP_LEFT = 10          # px zeroed at page edges (margin lines)
DEFAULT_PAGE_CROP_RIGHT = 15
DEFAULT_PAGE_CROP_TOP = 0
DEFAULT_PAGE_CROP_BOTTOM = 0

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
    threshold: float = DEFAULT_PARAGRAPH_THRESHOLD


@dataclass(frozen=True)
class QuestionConfig:
    header_height_factor: float = DEFAULT_HEADER_HEIGHT_FACTOR
    group_max_gap: int = DEFAULT_QUESTION_GROUP_MAX_GAP
    short_line_ratio: float = DEFAULT_QUESTION_SHORT_LINE_RATIO


@dataclass(frozen=True)
class AnswerConfig:
    trim_density_ratio: float = DEFAULT_ANSWER_TRIM_DENSITY_RATIO
    margin_scribble_px: int = DEFAULT_ANSWER_MARGIN_SCRIBBLE_PX
    min_ink_area: int = DEFAULT_ANSWER_MIN_INK_AREA


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
class PreprocessConfig:
    denoise_h: float = DEFAULT_DENOISE_H
    clahe_clip_limit: float = DEFAULT_CLAHE_CLIP_LIMIT
    clahe_grid: int = DEFAULT_CLAHE_GRID
    max_deskew_deg: float = DEFAULT_MAX_DESKEW_DEG
    adaptive_block_size: int = DEFAULT_ADAPTIVE_BLOCK_SIZE
    adaptive_c: int = DEFAULT_ADAPTIVE_C
    morph_close_size: int = DEFAULT_MORPH_CLOSE_SIZE
    morph_open_size: int = DEFAULT_MORPH_OPEN_SIZE


@dataclass(frozen=True)
class SegmentConfig:
    rule_kernel_width: int = DEFAULT_RULE_KERNEL_WIDTH
    margin_kernel_height: int = DEFAULT_MARGIN_KERNEL_HEIGHT
    rule_row_width_ratio: float = DEFAULT_RULE_ROW_WIDTH_RATIO
    rule_max_thickness: int = DEFAULT_RULE_MAX_THICKNESS
    line_gap_tolerance: int = DEFAULT_LINE_GAP_TOLERANCE
    min_row_ink: int = DEFAULT_MIN_ROW_INK
    min_line_ink_area: int = DEFAULT_MIN_LINE_INK_AREA
    word_gap_tolerance: int = DEFAULT_WORD_GAP_TOLERANCE
    min_col_ink: int = DEFAULT_MIN_COL_INK
    min_word_width: int = DEFAULT_MIN_WORD_WIDTH
    page_crop_left: int = DEFAULT_PAGE_CROP_LEFT
    page_crop_right: int = DEFAULT_PAGE_CROP_RIGHT
    page_crop_top: int = DEFAULT_PAGE_CROP_TOP
    page_crop_bottom: int = DEFAULT_PAGE_CROP_BOTTOM


@dataclass(frozen=True)
class Config:
    paragraph: ParagraphConfig = field(default_factory=ParagraphConfig)
    question: QuestionConfig = field(default_factory=QuestionConfig)
    answer: AnswerConfig = field(default_factory=AnswerConfig)
    highlight: HighlightConfig = field(default_factory=HighlightConfig)
    strikethrough: StrikethroughConfig = field(default_factory=StrikethroughConfig)
    caret: CaretConfig = field(default_factory=CaretConfig)
    confidence: ConfidenceConfig = field(default_factory=ConfidenceConfig)
    caret_anchor: CaretAnchorConfig = field(default_factory=CaretAnchorConfig)
    llm_review: LLMReviewConfig = field(default_factory=LLMReviewConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    ingestion: IngestionConfig = field(default_factory=IngestionConfig)
    preprocess: PreprocessConfig = field(default_factory=PreprocessConfig)
    segment: SegmentConfig = field(default_factory=SegmentConfig)


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
        threshold=_num(raw, "threshold", DEFAULT_PARAGRAPH_THRESHOLD),
    )


def _load_question(raw: dict[str, Any]) -> QuestionConfig:
    return QuestionConfig(
        header_height_factor=_num(raw, "header_height_factor", DEFAULT_HEADER_HEIGHT_FACTOR),
        group_max_gap=_int(raw, "group_max_gap", DEFAULT_QUESTION_GROUP_MAX_GAP),
        short_line_ratio=_num(raw, "short_line_ratio", DEFAULT_QUESTION_SHORT_LINE_RATIO),
    )


def _load_caret(raw: dict[str, Any]) -> CaretConfig:
    return CaretConfig(
        symbol_min=_int(raw, "symbol_min", DEFAULT_CARET_SYMBOL_MIN),
        symbol_max=_int(raw, "symbol_max", DEFAULT_CARET_SYMBOL_MAX),
        symbol_min_area=_int(raw, "symbol_min_area", DEFAULT_CARET_SYMBOL_MIN_AREA),
        symbol_max_area=_int(raw, "symbol_max_area", DEFAULT_CARET_SYMBOL_MAX_AREA),
        symbol_bottom_frac=_num(raw, "symbol_bottom_frac", DEFAULT_CARET_SYMBOL_BOTTOM_FRAC),
        symbol_below_slack=_int(raw, "symbol_below_slack", DEFAULT_CARET_SYMBOL_BELOW_SLACK),
        insert_above=_int(raw, "insert_above", DEFAULT_CARET_INSERT_ABOVE),
        insert_min_above=_int(raw, "insert_min_above", DEFAULT_CARET_INSERT_MIN_ABOVE),
        insert_max_dx=_int(raw, "insert_max_dx", DEFAULT_CARET_INSERT_MAX_DX),
        insert_max_width=_int(raw, "insert_max_width", DEFAULT_CARET_INSERT_MAX_WIDTH),
        insert_max_height=_int(raw, "insert_max_height", DEFAULT_CARET_INSERT_MAX_HEIGHT),
    )


def _load_strikethrough(raw: dict[str, Any]) -> StrikethroughConfig:
    return StrikethroughConfig(
        open_kernel=_int(raw, "open_kernel", DEFAULT_STRIKE_OPEN_KERNEL),
        min_stroke_len=_int(raw, "min_stroke_len", DEFAULT_STRIKE_MIN_STROKE_LEN),
        max_stroke_thickness=_int(raw, "max_stroke_thickness", DEFAULT_STRIKE_MAX_THICKNESS),
        join_gap=_int(raw, "join_gap", DEFAULT_STRIKE_JOIN_GAP),
        join_height=_int(raw, "join_height", DEFAULT_STRIKE_JOIN_HEIGHT),
        min_aspect=_int(raw, "min_aspect", DEFAULT_STRIKE_MIN_ASPECT),
        min_crossed_gap=_int(raw, "min_crossed_gap", DEFAULT_STRIKE_MIN_CROSSED_GAP),
    )


def _load_highlight(raw: dict[str, Any]) -> HighlightConfig:
    return HighlightConfig(
        hue_min=_int(raw, "hue_min", DEFAULT_HIGHLIGHT_HUE_MIN),
        hue_max=_int(raw, "hue_max", DEFAULT_HIGHLIGHT_HUE_MAX),
        sat_min=_int(raw, "sat_min", DEFAULT_HIGHLIGHT_SAT_MIN),
        sat_max=_int(raw, "sat_max", DEFAULT_HIGHLIGHT_SAT_MAX),
        val_min=_int(raw, "val_min", DEFAULT_HIGHLIGHT_VAL_MIN),
        val_max=_int(raw, "val_max", DEFAULT_HIGHLIGHT_VAL_MAX),
        cleanup_size=_int(raw, "cleanup_size", DEFAULT_HIGHLIGHT_CLEANUP_SIZE),
        min_area=_int(raw, "min_area", DEFAULT_HIGHLIGHT_MIN_AREA),
    )


def _load_answer(raw: dict[str, Any]) -> AnswerConfig:
    return AnswerConfig(
        trim_density_ratio=_num(raw, "trim_density_ratio", DEFAULT_ANSWER_TRIM_DENSITY_RATIO),
        margin_scribble_px=_int(raw, "margin_scribble_px", DEFAULT_ANSWER_MARGIN_SCRIBBLE_PX),
        min_ink_area=_int(raw, "min_ink_area", DEFAULT_ANSWER_MIN_INK_AREA),
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


def _load_preprocess(raw: dict[str, Any]) -> PreprocessConfig:
    block_size = _int(raw, "adaptive_block_size", DEFAULT_ADAPTIVE_BLOCK_SIZE)
    if block_size % 2 == 0:
        block_size += 1  # adaptiveThreshold requires an odd block size
    return PreprocessConfig(
        denoise_h=_num(raw, "denoise_h", DEFAULT_DENOISE_H),
        clahe_clip_limit=_num(raw, "clahe_clip_limit", DEFAULT_CLAHE_CLIP_LIMIT),
        clahe_grid=_int(raw, "clahe_grid", DEFAULT_CLAHE_GRID),
        max_deskew_deg=_num(raw, "max_deskew_deg", DEFAULT_MAX_DESKEW_DEG),
        adaptive_block_size=block_size,
        adaptive_c=_int(raw, "adaptive_c", DEFAULT_ADAPTIVE_C),
        morph_close_size=_int(raw, "morph_close_size", DEFAULT_MORPH_CLOSE_SIZE),
        morph_open_size=_int(raw, "morph_open_size", DEFAULT_MORPH_OPEN_SIZE),
    )


def _load_segment(raw: dict[str, Any]) -> SegmentConfig:
    return SegmentConfig(
        rule_kernel_width=_int(raw, "rule_kernel_width", DEFAULT_RULE_KERNEL_WIDTH),
        margin_kernel_height=_int(raw, "margin_kernel_height", DEFAULT_MARGIN_KERNEL_HEIGHT),
        rule_row_width_ratio=_num(raw, "rule_row_width_ratio", DEFAULT_RULE_ROW_WIDTH_RATIO),
        rule_max_thickness=_int(raw, "rule_max_thickness", DEFAULT_RULE_MAX_THICKNESS),
        line_gap_tolerance=_int(raw, "line_gap_tolerance", DEFAULT_LINE_GAP_TOLERANCE),
        min_row_ink=_int(raw, "min_row_ink", DEFAULT_MIN_ROW_INK),
        min_line_ink_area=_int(raw, "min_line_ink_area", DEFAULT_MIN_LINE_INK_AREA),
        word_gap_tolerance=_int(raw, "word_gap_tolerance", DEFAULT_WORD_GAP_TOLERANCE),
        min_col_ink=_int(raw, "min_col_ink", DEFAULT_MIN_COL_INK),
        min_word_width=_int(raw, "min_word_width", DEFAULT_MIN_WORD_WIDTH),
        page_crop_left=_int(raw, "page_crop_left", DEFAULT_PAGE_CROP_LEFT),
        page_crop_right=_int(raw, "page_crop_right", DEFAULT_PAGE_CROP_RIGHT),
        page_crop_top=_int(raw, "page_crop_top", DEFAULT_PAGE_CROP_TOP),
        page_crop_bottom=_int(raw, "page_crop_bottom", DEFAULT_PAGE_CROP_BOTTOM),
    )


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
        question=_load_question(raw.get("question", {}) or {}),
        answer=_load_answer(raw.get("answer", {}) or {}),
        highlight=_load_highlight(raw.get("highlight", {}) or {}),
        strikethrough=_load_strikethrough(raw.get("strikethrough", {}) or {}),
        caret=_load_caret(raw.get("caret", {}) or {}),
        confidence=_load_confidence(raw.get("confidence", {}) or {}),
        caret_anchor=_load_caret_anchor(raw.get("caret_anchor", {}) or {}),
        llm_review=_load_llm_review(raw.get("llm_review", {}) or {}),
        storage=_load_storage(raw.get("storage", {}) or {}),
        ingestion=_load_ingestion(raw.get("ingestion", {}) or {}),
        preprocess=_load_preprocess(raw.get("preprocess", {}) or {}),
        segment=_load_segment(raw.get("segment", {}) or {}),
    )


# Module-level default config — import this for quick access:
#   from config import CONFIG
CONFIG = load_config()
