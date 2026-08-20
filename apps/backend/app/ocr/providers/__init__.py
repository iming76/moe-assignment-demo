"""Vision LLM provider registry.

Each provider module exposes ``call(config, request, image) -> dict`` and
returns the same normalized ``{text, confidence, uncertainty}`` shape
regardless of its native request/response format.
"""

from __future__ import annotations

from typing import Any, Callable

from ...config import VisionLLMConfig
from . import openai, openrouter

ProviderCall = Callable[[VisionLLMConfig, dict[str, Any], bytes], dict[str, Any]]

PROVIDERS: dict[str, ProviderCall] = {
    "openai": openai.call,
    "openrouter": openrouter.call,
}
