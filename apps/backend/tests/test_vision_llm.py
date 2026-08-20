from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import json
import os
from unittest.mock import patch

from app.config import VisionLLMConfig
from app.ocr.providers import openai as openai_provider
from app.ocr.vision_llm import (
    LINE_TRANSCRIPTION_PROMPT,
    PROMPT_PATH,
    VisionLLMClient,
    parse_line_response,
    persist_ocr,
)
from app.schemas import OCRResult
from app.storage import StorageLayout


class VisionLLMTests(unittest.TestCase):
    def test_openai_ocr_result_is_persisted_by_vision_module(self):
        with TemporaryDirectory() as tmp:
            layout = StorageLayout("doc", tmp)
            result = OCRResult("line1", "literal", 0.95, "gpt-5.4-mini")
            path = persist_ocr(layout, 1, result)

            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["text"], "literal")

    def test_line_prompt_is_loaded_from_prompt_file(self):
        self.assertEqual(PROMPT_PATH.name, "line_transcription.md")
        self.assertEqual(
            LINE_TRANSCRIPTION_PROMPT,
            PROMPT_PATH.read_text(encoding="utf-8").strip(),
        )
        self.assertIn("<strikethrough>", LINE_TRANSCRIPTION_PROMPT)
        self.assertIn("<caret>", LINE_TRANSCRIPTION_PROMPT)
        self.assertIn("Never autocorrect spelling", LINE_TRANSCRIPTION_PROMPT)

    def test_openai_responses_payload_uses_image_and_strict_schema(self):
        captured = {}

        class FakeResponse:
            def __enter__(self):
                return self
            def __exit__(self, *_args):
                return False
            def read(self):
                return json.dumps({
                    "id": "resp_test",
                    "usage": {"input_tokens": 10, "output_tokens": 5},
                    "output": [{"type": "message", "content": [{
                        "type": "output_text",
                        "text": json.dumps({"text": "teh", "confidence": .94, "uncertainty": []}),
                    }]}],
                }).encode()

        def fake_urlopen(request, timeout):
            captured["payload"] = json.loads(request.data)
            captured["authorization"] = request.headers["Authorization"]
            captured["timeout"] = timeout
            return FakeResponse()

        cfg = VisionLLMConfig(provider="openai", model="gpt-5.4-mini",
                              endpoint="https://api.openai.com/v1/responses", api_key_env="OPENAI_API_KEY")
        request = {"type": "line_transcription", "instruction": "literal", "cropId": "line1"}
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}), patch("urllib.request.urlopen", fake_urlopen):
            result = openai_provider.call(cfg, request, b"png")

        self.assertEqual(result["text"], "teh")
        self.assertEqual(result["_openai"]["responseId"], "resp_test")
        self.assertEqual(captured["authorization"], "Bearer test-key")
        content = captured["payload"]["input"][0]["content"]
        self.assertTrue(content[1]["image_url"].startswith("data:image/png;base64,"))
        output_format = captured["payload"]["text"]["format"]
        self.assertEqual(output_format["type"], "json_schema")
        self.assertTrue(output_format["strict"])

    def test_valid_and_uncertain_line_responses(self):
        valid = parse_line_response({"text": "teh", "confidence": 0.97, "uncertainty": []}, "line1", "mock", "v1", "key")
        self.assertEqual(valid.text, "teh")
        self.assertEqual(valid.validationState, "valid")
        uncertain = parse_line_response({"text": "t?h", "confidence": 0.5, "uncertainty": [{"start": 1, "end": 2, "reason": "illegible"}]}, "line1", "mock", "v1", "key")
        self.assertEqual(uncertain.reviewState, "required")

    def test_malformed_line_response_escalates(self):
        malformed = parse_line_response({"text": "x"}, "line1", "mock", "v1", "key")
        self.assertEqual(malformed.validationState, "invalid")

    def test_cache_hit_does_not_consume_budget_and_cap_escalates(self):
        calls = []
        def provider(request, image):
            calls.append(request["cropId"])
            return {"text": "literal", "confidence": .9, "uncertainty": []}
        cfg = VisionLLMConfig(model="mock", max_calls_per_page=1, cache=True)
        client = VisionLLMClient(cfg, provider=provider)
        with TemporaryDirectory() as tmp:
            first = Path(tmp) / "one.png"; first.write_bytes(b"same")
            second = Path(tmp) / "two.png"; second.write_bytes(b"different")
            client.transcribe_line(first, "line1", 1)
            client.transcribe_line(first, "line1", 1)
            capped = client.transcribe_line(second, "line2", 1)
        self.assertEqual(len(calls), 1)
        self.assertEqual(capped.reviewRequiredReason, "page_call_cap_reached")


if __name__ == "__main__":
    unittest.main()
