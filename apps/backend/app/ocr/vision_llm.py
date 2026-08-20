from __future__ import annotations

import base64
import hashlib
import json
import os
import time
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from ..config import VisionLLMConfig
from ..schemas import OCRResult, UncertaintyRange
from ..storage import StorageLayout

Provider = Callable[[dict[str, Any], bytes], dict[str, Any]]

PROMPT_PATH = Path(__file__).with_name("prompts") / "line_transcription.md"
LINE_TRANSCRIPTION_PROMPT = PROMPT_PATH.read_text(encoding="utf-8").strip()

REQUEST_SCHEMA_VERSION = "vision-ocr-v1"

BACKEND_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(BACKEND_ROOT / ".env", override=False)
load_dotenv(BACKEND_ROOT.parent.parent / ".env", override=False)


@dataclass
class PageRequestBudget:
    limit: int
    calls: int = 0

    def consume(self) -> bool:
        if self.calls >= self.limit:
            return False
        self.calls += 1
        return True


@dataclass
class VisionLLMClient:
    config: VisionLLMConfig
    provider: Provider | None = None
    cache: dict[str, dict[str, Any]] = field(default_factory=dict)
    budgets: dict[int, PageRequestBudget] = field(default_factory=dict)
    cache_dir: Path | None = None
    layout: StorageLayout | None = None

    def __post_init__(self) -> None:
        if self.provider is None and self.config.provider == "openai":
            self.provider = self._openai_provider

    def transcribe_line(
        self, crop_path: Path, crop_id: str, page_number: int
    ) -> OCRResult:
        request = {
            "type": "line_transcription",
            "schemaVersion": REQUEST_SCHEMA_VERSION,
            "model": self.config.model,
            "instruction": LINE_TRANSCRIPTION_PROMPT,
            "cropId": crop_id,
            "responseSchema": {
                "text": "string",
                "confidence": "number[0,1]",
                "uncertainty": [
                    {"start": "integer", "end": "integer", "reason": "string"}
                ],
            },
        }
        image = crop_path.read_bytes()
        key = make_cache_key(image, request)
        raw, reason = self._request(request, image, key, page_number, crop_id)
        if raw is None:
            return OCRResult(
                cropId=crop_id,
                text="",
                confidence=0.0,
                model=self.config.model,
                requestSchemaVersion=REQUEST_SCHEMA_VERSION,
                cacheKey=key,
                validationState="unavailable",
                reviewState="required",
                reviewRequiredReason=reason,
            )
        return parse_line_response(
            raw, crop_id, self.config.model, REQUEST_SCHEMA_VERSION, key
        )

    def _request(
        self,
        request: dict[str, Any],
        image: bytes,
        key: str,
        page_number: int,
        crop_id: str,
    ) -> tuple[dict[str, Any] | None, str | None]:
        if self.config.cache and key in self.cache:
            return self.cache[key], None
        cache_path = self.cache_dir / f"{key}.json" if self.cache_dir else None
        if self.config.cache and cache_path is not None and cache_path.exists():
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            if isinstance(cached, dict):
                self.cache[key] = cached
                return cached, None
        if self.provider is None:
            return None, "provider_unavailable"
        budget = self.budgets.setdefault(
            page_number, PageRequestBudget(self.config.max_calls_per_page)
        )
        if not budget.consume():
            return None, "page_call_cap_reached"
        try:
            raw = self.provider(request, image)
        except (
            Exception
        ) as exc:  # provider errors must escalate, not abort the document
            return None, f"provider_failure:{type(exc).__name__}"
        if self.layout is not None:
            persist_llm_response(self.layout, page_number, crop_id, raw)
        if self.config.cache:
            self.cache[key] = raw
            if cache_path is not None:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(
                    json.dumps(raw, ensure_ascii=False), encoding="utf-8"
                )
        return raw, None

    def _openai_provider(self, request: dict[str, Any], image: bytes) -> dict[str, Any]:
        api_key = os.environ.get(self.config.api_key_env, "")
        if not api_key:
            raise RuntimeError(f"Missing {self.config.api_key_env}")
        schema = _line_schema()
        prompt = f"Request schema version: {request.get('schemaVersion', REQUEST_SCHEMA_VERSION)}\n{request['instruction']}"
        payload = {
            "model": self.config.model,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {
                            "type": "input_image",
                            "image_url": "data:image/png;base64,"
                            + base64.b64encode(image).decode("ascii"),
                            "detail": "high",
                        },
                    ],
                }
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": request["type"],
                    "strict": True,
                    "schema": schema,
                }
            },
        }
        body = json.dumps(payload).encode()
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        req = urllib.request.Request(
            self.config.endpoint, data=body, headers=headers, method="POST"
        )
        with urllib.request.urlopen(req, timeout=60) as response:
            value = json.loads(response.read())
        if not isinstance(value, dict):
            raise ValueError("Provider response must be a JSON object")
        output_text = _response_output_text(value)
        parsed = json.loads(output_text)
        if not isinstance(parsed, dict):
            raise ValueError("OpenAI structured output must be a JSON object")
        parsed["_openai"] = {"responseId": value.get("id"), "usage": value.get("usage")}
        return parsed


def _response_output_text(response: dict[str, Any]) -> str:
    for item in response.get("output", []):
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if isinstance(content, dict) and content.get("type") == "output_text":
                text = content.get("text")
                if isinstance(text, str):
                    return text
    raise ValueError("OpenAI response did not contain output_text")


def _line_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "uncertainty": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "start": {"type": "integer", "minimum": 0},
                        "end": {"type": "integer", "minimum": 1},
                        "reason": {"type": "string"},
                    },
                    "required": ["start", "end", "reason"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["text", "confidence", "uncertainty"],
        "additionalProperties": False,
    }


def persist_ocr(layout: StorageLayout, page_number: int, result: OCRResult) -> Path:
    """Persist one OpenAI OCR result as ``ocr/<page>/<cropId>.json``."""
    path = layout.ocr_json_path(page_number, result.cropId)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(result.to_json(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


def persist_llm_response(
    layout: StorageLayout, page_number: int, crop_id: str, raw: dict[str, Any]
) -> Path:
    """Persist one raw LLM response as ``llm/<page>/<cropId>.json``."""
    path = layout.llm_json_path(page_number, crop_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(raw, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def make_cache_key(image: bytes, request: dict[str, Any]) -> str:
    canonical = json.dumps(
        request, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    return hashlib.sha256(image + b"\0" + canonical).hexdigest()


def parse_line_response(
    raw: dict[str, Any], crop_id: str, model: str, schema_version: str, cache_key: str
) -> OCRResult:
    started = time.perf_counter()
    try:
        text = raw["text"]
        confidence = float(raw["confidence"])
        if not isinstance(text, str) or not 0 <= confidence <= 1:
            raise ValueError("invalid text or confidence")
        uncertainty = [
            UncertaintyRange.from_json(item) for item in raw.get("uncertainty", [])
        ]
        if any(u.start < 0 or u.end <= u.start for u in uncertainty):
            raise ValueError("uncertainty range outside literal text")
        clamped = False
        for u in uncertainty:
            if u.end > len(text):
                u.end = len(text)
                clamped = True
        uncertainty = [u for u in uncertainty if u.end > u.start]
    except (KeyError, TypeError, ValueError) as exc:
        return OCRResult(
            cropId=crop_id,
            text="",
            confidence=0.0,
            model=model,
            rawResponse=raw,
            requestSchemaVersion=schema_version,
            cacheKey=cache_key,
            validationState="invalid",
            reviewState="required",
            reviewRequiredReason=f"malformed_response:{exc}",
        )
    return OCRResult(
        cropId=crop_id,
        text=text,
        confidence=confidence,
        model=model,
        rawResponse=raw,
        requestSchemaVersion=schema_version,
        cacheKey=cache_key,
        uncertainty=uncertainty,
        validationState="valid",
        reviewState="required" if uncertainty else "pending",
        reviewRequiredReason=(
            "uncertainty_range_clamped"
            if clamped
            else "model_uncertainty" if uncertainty else None
        ),
        processingTimeMs=int((time.perf_counter() - started) * 1000),
    )
