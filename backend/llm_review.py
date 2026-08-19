"""Optional LLM ambiguity review — Trigger A: ambiguous caret anchor (task 16a).

Spec Section 39.1.2: deterministic gap projection first; escalate only on
ambiguity (two gaps within gap_epsilon_px, caret inside a word bbox,
clustered/orphan carets, low anchor-line confidence, unclear line). The LLM
is asked multiple choice over numbered tick-mark positions; invalid indices
are rejected and the deterministic guess is kept.

Full module grows in tasks 16b (low-confidence trigger) and 16c (plumbing).
"""

from __future__ import annotations

import hashlib
import time
from typing import Callable, Optional

import config as config_module
from reconstruct import anchor_caret_deterministic
from schemas import BoundingBox, Caret, Document, LLMReview, OCRResult

# A pluggable vision-LLM client: payload dict -> raw response dict (or None).
LLMClient = Callable[[dict], Optional[dict]]


def _no_client(payload: dict) -> Optional[dict]:
    return None


class LLMReviewStage:
    def __init__(self, client: Optional[LLMClient] = None) -> None:
        self.client = client or _no_client
        self._cache: dict[str, LLMReview] = {}
        self._calls_per_page: dict[int, int] = {}

    # ------------------------------------------------------------------ 16a
    def caret_anchor_reviews(
        self,
        page_number: int,
        carets: list[Caret],
        lines_by_id: dict[str, list[BoundingBox]],
        line_confidence: dict[str, float],
    ) -> list[LLMReview]:
        cfg = config_module.CONFIG.llm_review
        reviews: list[LLMReview] = []
        seen_xs: list[float] = []
        for caret in carets:
            words = lines_by_id.get(caret.anchorLineId, [])
            gap_idx, ambiguous, candidates = anchor_caret_deterministic(caret, words)
            cx = caret.caret.get("bbox", {}).get("x")
            reasons = []
            if ambiguous:
                reasons.append("two_gaps_within_epsilon")
            if cx is not None and any(w.x < cx < w.x + w.width for w in words):
                reasons.append("caret_inside_word")
            if cx is not None and any(abs(cx - s) <= 10 for s in seen_xs):
                reasons.append("clustered_carets")
            if cx is not None:
                seen_xs.append(cx)
            if not words:
                reasons.append("unclear_line")
            conf = line_confidence.get(caret.anchorLineId)
            if conf is not None and conf < cfg.triggers.low_confidence.threshold:
                reasons.append("low_anchor_confidence")
            if not reasons:
                continue
            review = self._ask(
                page_number,
                trigger="caret_anchor_ambiguity",
                target_id=caret.id,
                crop_paths=[caret.insertCrop] if caret.insertCrop else [],
                candidates=[f"gap {i + 1}" for i in range(max(1, len(words) - 1))],
                raw_payload={
                    "question": "Which numbered tick mark is the caret anchor?",
                    "reasons": reasons,
                    "deterministic_guess": gap_idx,
                    "candidates": list(range(len(words) - 1)),
                },
                valid=lambda resp: _valid_anchor(resp, len(words) - 1),
                fallback=gap_idx,
                agreed=lambda chosen: chosen == gap_idx,
            )
            if review is not None:
                caret.llmReview = review
                caret.anchorCandidates = candidates
                reviews.append(review)
        return reviews

    # ------------------------------------------------------------------ 16b
    def low_confidence_reviews(
        self, page_number: int, results: list[OCRResult]
    ) -> list[LLMReview]:
        """Spec 39.1.3: <0.70 always sent; 0.70-0.89 only when configured;
        >=0.90 never. The LLM selects among TrOCR N-best candidates by index;
        a free-form fallback is diff-validated against top-1 and rejected on
        signs of normalization."""
        cfg = config_module.CONFIG.llm_review
        low = cfg.triggers.low_confidence
        reviews: list[LLMReview] = []
        for result in results:
            if result.confidence >= config_module.CONFIG.confidence.accept_threshold:
                continue  # >= 0.90 is never sent
            if (
                result.confidence >= low.threshold
                and not low.include_review_recommended
            ):
                continue  # 0.70-0.89 only when configured
            candidates = [c["text"] for c in result.candidates] or [result.text]
            review = self._ask(
                page_number,
                trigger="low_confidence",
                target_id=result.cropId,
                crop_paths=[result.cropId],
                candidates=candidates,
                raw_payload={
                    "question": "Select the candidate index matching the ink.",
                    "candidates": candidates,
                    "top1": result.text,
                },
                valid=lambda resp, cands=candidates: _valid_choice(resp, cands),
                fallback=0,
                agreed=lambda chosen: chosen == 0,
            )
            if review is not None:
                result.llmReview = review
                reviews.append(review)
        return reviews

    def _ask(
        self,
        page_number: int,
        trigger: str,
        target_id: str,
        crop_paths: list[str],
        candidates: list[str],
        raw_payload: dict,
        valid: Callable[[dict], bool],
        fallback,
        agreed: Callable,
    ) -> Optional[LLMReview]:
        cfg = config_module.CONFIG.llm_review
        if not cfg.enabled:
            return None
        if self._calls_per_page.get(page_number, 0) >= cfg.max_calls_per_page:
            return None  # per-page call cap

        cache_key = hashlib.sha256(
            (target_id + "|".join(crop_paths) + "|".join(candidates)).encode()
        ).hexdigest()
        if cfg.cache and cache_key in self._cache:
            return self._cache[cache_key]

        started = time.perf_counter()
        raw = self.client(raw_payload)
        latency = int((time.perf_counter() - started) * 1000)
        self._calls_per_page[page_number] = self._calls_per_page.get(page_number, 0) + 1

        chosen = fallback
        if raw is not None and valid(raw):
            chosen = raw.get("chosen", raw.get("anchorIndex", raw.get("index", fallback)))

        review = LLMReview(
            id=f"llm_{target_id}",
            targetId=target_id,
            trigger=trigger,
            inputs={"cropPaths": crop_paths, "candidates": candidates},
            rawResponse=raw,
            chosen=chosen,
            agreedWithDeterministic=bool(agreed(chosen)),
            applied=False,  # until a human confirms
            model=cfg.model,
            latencyMs=latency,
        )
        if cfg.cache:
            self._cache[cache_key] = review
        return review


def run_llm_review(
    document: Document,
    client: Optional[LLMClient] = None,
    words_by_line_id: Optional[dict[str, list[BoundingBox]]] = None,
) -> list[LLMReview]:
    """Spec 39.1.7: after reconstruction, before human review.

    enabled=false yields zero behavior change (no client calls, no records).
    The full page image is never sent — only target crops and spatial
    metadata (see _ask payloads).
    """
    if not config_module.CONFIG.llm_review.enabled:
        return []
    stage = LLMReviewStage(client)
    provided = words_by_line_id or {}
    all_reviews: list[LLMReview] = []
    for page in document.pages:
        lines_by_id: dict[str, list[BoundingBox]] = {}
        line_conf: dict[str, float] = {}
        ocr_by_crop = {o.cropId: o for o in page.ocr}
        if page.answer:
            for para in page.answer.paragraphs:
                for line in para.lines:
                    lines_by_id[line.id] = provided.get(line.id, [])
                    res = ocr_by_crop.get(line.cropId)
                    if res:
                        line_conf[line.id] = res.confidence
        all_reviews += stage.caret_anchor_reviews(
            page.pageNumber, page.carets, lines_by_id, line_conf
        )
        all_reviews += stage.low_confidence_reviews(page.pageNumber, page.ocr)
    document.llmReviews += all_reviews
    return all_reviews


def _valid_anchor(resp: dict, n_gaps: int) -> bool:
    idx = resp.get("anchorIndex", resp.get("chosen", resp.get("index")))
    return isinstance(idx, int) and 0 <= idx < n_gaps


def _valid_choice(resp: dict, candidates: list[str]) -> bool:
    idx = resp.get("index", resp.get("chosen"))
    if isinstance(idx, int) and 0 <= idx < len(candidates):
        return True
    text = resp.get("text")
    if isinstance(text, str) and candidates:
        top1 = candidates[0]
        if _looks_normalized(text, top1):
            return False  # autocorrect signs → reject
        return _char_diff_ok(text, top1)
    return False


def _looks_normalized(text: str, top1: str) -> bool:
    """Signs of autocorrection: changed case or fixed punctuation."""
    if text == top1:
        return False
    return text.lower() == top1.lower() or text.capitalize() == top1.capitalize()


def _char_diff_ok(text: str, top1: str) -> bool:
    import difflib

    return difflib.SequenceMatcher(None, text, top1).ratio() >= 0.8
