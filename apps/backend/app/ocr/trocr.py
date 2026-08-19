"""TrOCR line-crop runner (task 13).

Spec Sections 23-25: TrOCR operates on line-level crops only and returns
literal text + confidence + model provenance. No correction of any kind —
no spelling, grammar, punctuation, capitalization, or language changes.
Beam search produces N-best candidates (all derived from the same ink) for
the review stage.

Per-crop OCR JSON is persisted to ocr/<page>/<cropId>.json (spec Section 37).
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import cv2

from ..config import CONFIG
from ..schemas import OCRResult, OCRToken
from ..storage import StorageLayout

MODEL_NAME = "microsoft/trocr-base-handwritten"

_processor = None
_model = None


def _load():
    global _processor, _model
    if _model is None:
        from transformers import (
            RobertaTokenizer,
            TrOCRProcessor,
            ViTImageProcessor,
            VisionEncoderDecoderModel,
        )

        # The hub repo ships vocab.json/merges.txt only (no tokenizer.json),
        # so the fast-tokenizer auto-path fails; build the processor from the
        # slow RoBERTa tokenizer explicitly.
        tokenizer = RobertaTokenizer.from_pretrained(MODEL_NAME)
        image_processor = ViTImageProcessor.from_pretrained(MODEL_NAME)
        _processor = TrOCRProcessor(image_processor=image_processor, tokenizer=tokenizer)
        _model = VisionEncoderDecoderModel.from_pretrained(MODEL_NAME)
        _model.eval()
    return _processor, _model


def run_line_crop(
    crop_path: Path,
    num_beams: int = 5,
) -> OCRResult:
    """Transcribe one line crop literally. Never corrects the output."""
    processor, model = _load()

    image = cv2.imread(str(crop_path))
    if image is None:
        raise FileNotFoundError(f"Line crop not found: {crop_path}")
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

    started = time.perf_counter()
    pixel_values = processor(image, return_tensors="pt").pixel_values

    gen = model.generate(
        pixel_values,
        num_beams=num_beams,
        num_return_sequences=num_beams,
        max_new_tokens=CONFIG.ocr.max_new_tokens,
        output_scores=True,
        return_dict_in_generate=True,
    )
    elapsed_ms = int((time.perf_counter() - started) * 1000)

    texts = processor.batch_decode(gen.sequences, skip_special_tokens=True)
    confidences = _sequence_confidences(gen, num_beams)

    candidates = [
        {"text": t, "confidence": round(c, 4)} for t, c in zip(texts, confidences)
    ]

    return OCRResult(
        cropId=Path(crop_path).stem,
        text=texts[0],
        confidence=round(confidences[0], 4),
        model=MODEL_NAME,
        candidates=candidates,
        processingTimeMs=elapsed_ms,
    )


def _sequence_confidences(gen, num_beams: int) -> list[float]:
    """Per-sequence confidence = exp(mean log-prob over generated tokens)."""
    import torch

    _, model = _load()
    eos_id = int(model.config.decoder.eos_token_id)
    scores = gen.sequences_scores
    lengths = (gen.sequences != eos_id).sum(-1).clamp(min=1)
    mean_logp = scores / lengths.float()
    return [float(torch.exp(s).clamp(0.0, 1.0)) for s in mean_logp]


def persist_ocr(layout: StorageLayout, page_number: int, result: OCRResult) -> Path:
    """Write ocr/<page>/<cropId>.json (spec Section 37)."""
    path = layout.ocr_json_path(page_number, result.cropId)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result.to_json(), indent=2, ensure_ascii=False), encoding="utf-8")
    return path
