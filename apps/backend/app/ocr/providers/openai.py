"""OpenAI provider — Responses API with strict JSON-schema structured output."""

from __future__ import annotations

import base64
import json
from typing import Any

from ...config import VisionLLMConfig
from ._shared import build_prompt, line_schema, post_json, require_api_key


def call(config: VisionLLMConfig, request: dict[str, Any], image: bytes) -> dict[str, Any]:
    api_key = require_api_key(config)
    payload = {
        "model": config.model,
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": build_prompt(request)},
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
                "schema": line_schema(),
            }
        },
    }
    value = post_json(config.endpoint, {"Authorization": f"Bearer {api_key}"}, payload)
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
