# Proposal: Handwritten Student Script OCR & Reconstruction

## Why

Student scripts must be transcribed with character-level fidelity — spelling errors, cancelled text, caret insertions, highlights, and punctuation are evidence, not mistakes to fix. No existing pipeline gives us traceable, crop-backed transcription where every extracted fragment links back to the original image, and where a human reviewer can verify OCR against the visual source of truth. This is the POC/MVP build of that pipeline (spec v1.0).

## What Changes

- Build a Python backend pipeline (FastAPI + OpenCV + TrOCR) that ingests handwritten scripts as PNG/JPG/JPEG/WEBP images or scanned/multi-page PDFs and renders PDFs into page images without touching the original file.
- Implement spatial analysis with OpenCV: question detection and multi-line grouping, answer-region detection, logical paragraph detection/splitting before OCR, line segmentation, plus highlight, strikethrough, and caret detection.
- Persist every crop (question, answer, paragraph, line, word, cancelled, caret) with metadata before OCR runs; crops are immutable so OCR models can be swapped without re-segmenting.
- Run TrOCR on line-level crops only, storing literal text, confidence, and model provenance. No autocorrect, grammar fixing, punctuation normalization, or translation anywhere in the pipeline.
- Build a reconstruction engine that merges OCR text with spatial/markup metadata into final output: `<strikethrough>` for cancelled text, `<caret>` insertions at their logical position, physical line breaks joined, paragraphs separated by `\n\n`.
- Add an optional, disabled-by-default LLM ambiguity review stage (gated, multiple-choice only, non-authoritative) for ambiguous caret anchors and low-confidence OCR regions.
- Add a human review flow with configurable confidence thresholds (>= 0.90 accepted, 0.70–0.89 review recommended, < 0.70 review required).
- Build a Next.js/TypeScript frontend review tool: original-image viewer with zoom/pan, toggleable overlays (questions, answers, paragraphs, lines, highlights, strikethroughs, carets), crop inspector, paragraph navigation, and manual correction.
- Track the full processing state machine (UPLOADED → … → APPROVED → EXPORTED) and retain all intermediate artifacts for debugging.
- Establish the monorepo: Turborepo + pnpm workspaces (`apps/web`, `packages/types`) with the Python backend outside turbo; `packages/types` mirrors backend JSON schemas.

## Capabilities

### New Capabilities

- `document-ingestion`: Accept PNG/JPG/JPEG/WEBP and scanned/multi-page PDFs; render PDF pages to images; preserve originals untouched; normalize everything into a PageImage representation.
- `spatial-detection`: OpenCV-driven preprocessing, question detection with multi-line grouping, answer-region detection, and logical paragraph detection/splitting that happens before detailed OCR.
- `markup-detection`: Independent detection of highlights, strikethroughs, and caret insertions as spatial metadata that never alters OCR text.
- `crop-management`: Generate, persist, and catalog immutable crops (question/answer/paragraph/line/word/cancelled/caret) with bounding-box metadata before any OCR runs.
- `ocr-transcription`: TrOCR over line-level crops producing literal text with confidence scores under strict fidelity rules (no spelling, grammar, punctuation, capitalization, or language changes).
- `markup-reconstruction`: Combine OCR text with spatial and markup metadata into final transcription — strikethrough/caret markup at correct logical positions, line joining, paragraph separation, and the complete internal JSON.
- `llm-ambiguity-review`: Optional, disabled-by-default, final-stage LLM review limited to ambiguous caret anchors and low-confidence regions, using multiple-choice selection over ink-derived candidates with suggestions left `applied: false` until human confirmation.
- `human-review`: Review state machine, configurable confidence thresholds, low-confidence flagging, manual correction, and approval before export.
- `review-frontend`: Next.js review UI — original image viewer, toggleable overlays, crop inspector, paragraph navigation, confidence visualization, and text correction.
- `pipeline-orchestration`: End-to-end pipeline wiring, processing state machine, artifact retention, and the storage directory structure.

### Modified Capabilities

None — this is a greenfield build; `openspec/specs/` is empty.

## Impact

- **New code**: `backend/` (Python: FastAPI, OpenCV, PyTorch/Transformers TrOCR, Pillow, PyMuPDF), `apps/web/` (Next.js + TypeScript), `packages/types/` (shared TS types), monorepo config (`turbo.json`, `pnpm-workspace.yaml`).
- **New dependencies**: Python — opencv-python, torch, transformers, pillow, PyMuPDF, fastapi; JS — Next.js, React, TypeScript, Turborepo, pnpm workspaces.
- **Storage**: local `storage/` tree (originals, rendered, processed, crops, ocr, output) retained for debugging and model iteration.
- **Data contracts**: `packages/types` mirrors backend JSON schemas — both sides share one contract.
- **Out of scope (POC)**: security, authentication, hardening, production readiness, deployment. LLM review is optional and disabled by default.
