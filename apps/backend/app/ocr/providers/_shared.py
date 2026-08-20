"""Helpers shared by the vision LLM provider implementations."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from ...config import VisionLLMConfig
from ...logging_config import get_llm_logger

REQUEST_SCHEMA_VERSION = "vision-ocr-v1"

_TRUNCATE_AT = 300  # chars; keeps base64 image/response blobs out of the logs


def _redact(value: Any) -> Any:
    """Deep-copy `value`, truncating any long string (image data, huge responses)."""
    if isinstance(value, dict):
        return {k: _redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(v) for v in value]
    if isinstance(value, str) and len(value) > _TRUNCATE_AT:
        return f"<{len(value)} chars omitted>"
    return value


def require_api_key(config: VisionLLMConfig) -> str:
    api_key = os.environ.get(config.api_key_env, "")
    if not api_key:
        raise RuntimeError(f"Missing {config.api_key_env}")
    return api_key


def build_prompt(request: dict[str, Any]) -> str:
    version = request.get("schemaVersion", REQUEST_SCHEMA_VERSION)
    return f"Request schema version: {version}\n{request['instruction']}"


def post_json(url: str, headers: dict[str, str], payload: dict[str, Any]) -> dict[str, Any]:
    logger = get_llm_logger()
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json", **headers}, method="POST"
    )
    logger.info("request POST %s payload=%s", url, json.dumps(_redact(payload), ensure_ascii=False))
    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            raw_bytes = response.read()
            status = getattr(response, "status", None)
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        logger.error("response %s status=%s body=%s", url, exc.code, error_body[:_TRUNCATE_AT * 4])
        raise RuntimeError(f"{url} returned HTTP {exc.code}: {error_body}") from exc
    except urllib.error.URLError as exc:
        logger.error("request failed %s reason=%s", url, exc.reason)
        raise RuntimeError(f"{url} request failed: {exc.reason}") from exc

    try:
        value = json.loads(raw_bytes)
    except json.JSONDecodeError as exc:
        logger.error("response %s status=%s non-json body=%s", url, status, raw_bytes[:_TRUNCATE_AT * 4])
        raise ValueError(f"{url} returned non-JSON response") from exc
    logger.info("response %s status=%s body=%s", url, status, json.dumps(_redact(value), ensure_ascii=False))
    if not isinstance(value, dict):
        raise ValueError("Provider response must be a JSON object")
    return value


def parse_json_object(text: str) -> dict[str, Any]:
    """Parse a JSON object out of model text, tolerating leading/trailing prose."""
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise ValueError("Response did not contain a JSON object")
        parsed = json.loads(text[start : end + 1])
    if not isinstance(parsed, dict):
        raise ValueError("Response JSON must be an object")
    return parsed


def line_schema() -> dict[str, Any]:
    """JSON Schema (draft-style) for the {text, confidence, uncertainty} response."""
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
