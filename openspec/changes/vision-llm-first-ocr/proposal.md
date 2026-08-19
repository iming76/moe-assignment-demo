## Why

The current pipeline retains an unused local TrOCR rollback alongside OpenAI.
The POC only needs reliable literal OCR from each detected handwriting line. A
constrained Vision LLM can fully replace TrOCR and preserve visible caret and
strikethrough semantics without separate OpenCV detection and classification stages.

## What Changes

- Remove TrOCR and use OpenAI Vision LLM transcription as the only OCR runner
  for persisted line crops.
- Submit only line crops to the model; prompt the model to preserve visible
  cancelled and inserted writing using `<strikethrough>` and `<caret>` tags,
  without separate detectors or correction-context crops.
- Require structured results containing literal line text, confidence, and
  uncertainty ranges.
- Add validation, per-page limits, caching, and review escalation.
- Keep reconstruction and human review focused on line OCR provenance.

## Capabilities

### New Capabilities
- `vision-llm-transcription`: Performs fidelity-constrained line transcription
  from immutable line crops.

### Modified Capabilities
- `crop-management`: Keeps immutable line crops as model input artifacts.
- `ocr-transcription`: Replaces primary TrOCR with Vision LLM line OCR.
- `markup-detection`: Removes separate caret and strikethrough detectors from
  the active pipeline; the line model preserves visible markup in its text.
- `markup-reconstruction`: Joins literal tagged lines within paragraphs and
  preserves paragraph boundaries with `\n\n`.
- `human-review`: Exposes uncertain or invalid line OCR and provenance.
- `pipeline-orchestration`: Uses one Vision LLM stage before reconstruction.
- `review-frontend`: Displays line-crop evidence and line review state.

## Impact

- **Backend:** OpenAI-only line transcription, validation, persistence, caching,
  and request caps; no TrOCR or correction-candidate analysis.
- **Data contracts:** OCR provenance and review fields remain; correction
  candidate contracts leave the active API.
- **Workflow:** every model call corresponds to one persisted line crop.
