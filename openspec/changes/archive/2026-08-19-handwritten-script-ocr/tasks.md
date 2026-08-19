# Tasks: Handwritten Student Script OCR & Reconstruction

Numbering: plain numbers run sequentially (each depends on the previous); letters (a, b, c) beside a number mark tasks that can run concurrently.

## 1. Monorepo & Foundation

- [x] 1-Scaffold monorepo: turbo.json, pnpm-workspace.yaml, apps/web (Next.js + TypeScript), packages/types, backend/ skeleton; Python backend stays outside turbo
- [x] 2a-Implement shared data schemas in backend/schemas.py (PageImage, BoundingBox, Question, Paragraph, Crop, OCRResult, LLMReview, full document JSON)
- [x] 2b-Implement mirrored TypeScript contract in packages/types matching backend JSON schemas
- [x] 3-Implement config module: named constants + YAML loader for paragraph weights, confidence thresholds, gap epsilon, and llm_review settings (enabled: false default)
- [x] 4-Implement storage layout helpers (originals/rendered/processed/crops/ocr/output) and document state machine module (UPLOADED → … → EXPORTED)

## 2. Document Ingestion

- [x] 5a-Implement image input normalization: PNG/JPG/JPEG/WEBP → PageImage with pageNumber, path, width, height, dpi; reject unsupported formats with a clear error
- [x] 5b-Implement PDF page rendering: scanned/image-based/multi-page PDF → per-page images via PyMuPDF; original preserved byte-for-byte in originals/
- [x] 6-Implement image preprocessing pipeline: grayscale, denoise, contrast normalization, deskew, threshold, morphology; persist intermediates to processed/<page>/, rendered image stays available

## 3. Spatial Detection

- [x] 7-Implement question detection: Q1/Q2/QN 1/Question prefixes, question marks, position and spacing signals; question recorded before answer processing
- [x] 8-Implement question line grouping: merge physical lines of one question into a single question text with no internal line breaks
- [x] 9-Implement answer region detection: bbox after question using vertical position, blank-line spacing, handwriting density, indentation; exclude page headers
- [x] 10-Implement paragraph boundary detection and splitting: weighted score (vertical gap primary + indentation + density, configurable weights), split before detailed OCR, unique paragraph IDs and order, one crop region per paragraph

## 4. Markup Detection

- [x] 11a-Implement highlight detection: RGB→HSV color mask, morphological cleanup, contours → highlight bbox + polygon metadata; must not alter OCR text
- [x] 11b-Implement strikethrough detection: long diagonal/horizontal strokes crossing handwriting, orientation/length/overlap signals → cancelled region associated with text span
- [x] 11c-Implement caret detection: caret symbol bbox, inserted-text crop, anchor line ID

## 5. Crops & OCR

- [x] 12-Implement crop generator: persist question/answer/paragraph/line/word/cancelled/caret crops with full metadata (id, type, pageNumber, parentId, path, bbox, createdAt) before any OCR runs; crops immutable once written
- [x] 13-Implement TrOCR line-crop runner: literal text + confidence + model per line crop, no correction of any kind; beam search N-best candidates available for review stage

## 6. Reconstruction & Review

- [x] 14-Implement reconstruction engine: caret text inserted at logical position wrapped in <caret>, cancelled text wrapped in <strikethrough>, physical line breaks joined with spaces, paragraphs separated by \n\n, full internal JSON assembled (documentId, source, pages, final)
- [x] 15-Implement human review flow: Review Required state after reconstruction, configurable confidence flagging (>=0.90 accepted / 0.70–0.89 recommended / <0.70 required), manual corrections recorded, approval → APPROVED → export final JSON
- [x] 16a-Implement LLM caret-anchor trigger: deterministic gap projection first; escalate only on ambiguity (two gaps within epsilon, caret inside word bbox, clustered/orphan carets, low anchor confidence, unclear line); multiple-choice request over numbered tick-mark crop; reject invalid anchorIndex and keep deterministic guess
- [x] 16b-Implement LLM low-confidence trigger: <0.70 sent (0.70–0.89 only if include_review_recommended, >=0.90 never); select among TrOCR N-best candidates by index; free-form fallback diff-validated against top-1 and rejected if normalized
- [x] 16c-Implement LLM review plumbing: LLMReview records (trigger, inputs, rawResponse, chosen, agreedWithDeterministic, applied, model, latencyMs), applied=false until human confirms, per-page call cap + caching, enabled=false yields zero behavior change; full page image never sent

## 7. Backend Wiring

- [x] 17-Implement pipeline.py orchestrator: wire all stage modules in order, advance state machine per stage, verify all artifacts retained per storage layout
- [x] 18-Implement FastAPI endpoints: upload document, get document state and full JSON, serve originals/rendered/crop images, submit review corrections, approve and export

## 8. Frontend

- [x] 19a-Implement image viewer: zoom, pan, page navigation, original resolution
- [x] 19b-Implement toggleable SVG overlays (question, answer, paragraphs, lines, highlights, strikethrough, carets) drawn in original image coordinate system
- [x] 19c-Implement crop inspector: click an object → original location, corresponding crop, TrOCR result, final reconstructed text
- [x] 19d-Implement paragraph navigation tree (Question → Answer → Paragraph N) with bbox highlight, line crops, markup display, OCR confidence flagging, and manual correction editor
- [ ] 20-Wire frontend to backend API consuming packages/types as the single shared contract

## 9. Verification

- [ ] 21-End-to-end verification on data/ocr-assessment-sample.png: run the full pipeline, walk the Section 42 acceptance criteria checklist (input, question, answer, OCR, markup, formatting, frontend, LLM-review-disabled default), fix gaps
