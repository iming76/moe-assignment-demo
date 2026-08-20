"""OpenRouter provider — Chat Completions shape, not OpenAI's Responses API."""

from __future__ import annotations

import base64
from typing import Any

from ...config import VisionLLMConfig
from ._shared import build_prompt, line_schema, parse_json_object, post_json, require_api_key


def call(config: VisionLLMConfig, request: dict[str, Any], image: bytes) -> dict[str, Any]:
    api_key = require_api_key(config)
    payload = {
        "model": config.model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": build_prompt(request)},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": "data:image/png;base64,"
                            + base64.b64encode(image).decode("ascii")
                        },
                    },
                ],
            }
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": request["type"],
                "strict": True,
                "schema": line_schema(),
            },
        },
    }
    value = post_json(config.endpoint, {"Authorization": f"Bearer {api_key}"}, payload)
    try:
        content = value["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("OpenRouter response missing choices[0].message.content") from exc
    # Not every OpenRouter model honors response_format strictly, so fall back to
    # extracting the first JSON object from free text.
    parsed = parse_json_object(content)
    parsed["_openrouter"] = {"id": value.get("id"), "usage": value.get("usage")}
    return parsed
