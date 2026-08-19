## Context

OpenCV remains responsible for normalization, structural regions, and line
segmentation. OpenAI receives only immutable line crops. Caret and strikethrough
semantics are not separately detected by OpenCV; the model preserves visible
markup using explicit tags, and ambiguous writing stays visible for review.

## Goals / Non-Goals

**Goals:**

- Make OpenAI the primary transcriber of compact line crops.
- Remove the unused TrOCR model and rollback branches.
- Preserve literal writing without normalization.
- Make results traceable, cacheable, validated, and reviewable.

**Non-Goals:**

- Sending full pages or paragraph crops to the model.
- Separate OpenCV detection or correction-candidate classification for caret
  insertions or strikethroughs.
- Automatic correction, grading, or language normalization.

## Decisions

### Line crops are the only model input

The pipeline submits one persisted line crop per request. Paragraph and word
crops may remain structural/review artifacts but are not model inputs.

### Structured responses are validated locally

Each request uses a versioned strict JSON schema containing literal text,
confidence, and uncertainty ranges. Invalid or unavailable output requires review.

### Cache and limits are per page

Cache keys cover image bytes, request type, model, schema, and prompt version.
Cache hits do not consume the page allowance.

### One model stage precedes reconstruction

`OCR_PROCESSING` transcribes line crops, then reconstruction joins physical
lines with spaces inside paragraphs and joins paragraphs with `\n\n`. The line
prompt requires visible cancelled text to use `<strikethrough>` tags and visible
caret insertions to use `<caret>` tags. There is no `CORRECTION_ANALYSIS` stage.

## Risks / Trade-offs

- [The model normalizes handwriting] → strict prompts and human review.
- [Provider cost or latency grows] → line crops, cache, and page caps.
- [A line crop does not show enough caret context] → retain the literal crop and
  uncertainty for reviewer edits.

## Migration Plan

1. Move OCR-result persistence into the OpenAI transcription module.
2. Remove TrOCR inference, dependencies, and disabled/shadow branches.
3. Keep immutable line artifacts, caching, caps, and review escalation.

## Implementation Selection

- Provider: OpenAI Responses API.
- OCR engine: OpenAI only; no local model fallback.
- Model: `gpt-5.4-mini`.
- Output: strict `text.format` JSON schema plus local validation.
- Credential: server-side `OPENAI_API_KEY` from backend or repository `.env`.

## Open Questions

- Representative cost, latency, uncertainty, and reviewer-acceptance metrics
  remain to be collected before production use.
