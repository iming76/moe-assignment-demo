## 1. Contracts and Configuration

- [x] 1.1 Add Vision LLM OCR provenance, uncertainty, validation, and review state to backend/frontend contracts.
- [x] 1.2 Configure OpenAI provider/model, schema version, page call cap, and cache policy.

## 2. Vision LLM Line Transcription

- [x] 2.1 Implement strict literal transcription of immutable line crops with local response validation.
- [x] 2.2 Add persistent caching, per-page accounting, and review escalation.
- [x] 2.3 Add mocked OpenAI tests for valid, uncertain, malformed, cache-hit, and call-cap outcomes.
- [x] 2.4 Store the line OCR prompt in a dedicated file and require literal
  strikethrough/caret tags plus paragraph-format preservation, with tests.

## 3. Line-Only Pipeline Simplification

- [x] 3.1 Remove active strikethrough/caret detection, evidence crops, correction candidates, and correction-context crops.
- [x] 3.2 Submit only line crops during OCR_PROCESSING and remove CORRECTION_ANALYSIS.
- [x] 3.3 Simplify reconstruction, API/frontend review contracts, overlays, actions, and tests to line OCR only.

## 4. Verification and Migration

- [x] 4.1 Remove TrOCR, its dependencies and fallback modes; retain OCR JSON persistence and immutable line-crop reuse.
- [ ] 4.2 Run strict OpenSpec validation and backend/frontend tests; document measured OpenAI cost, latency, uncertainty, and reviewer acceptance.
