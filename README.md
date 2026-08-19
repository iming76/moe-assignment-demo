# moe-research — Handwritten Student Script OCR & Reconstruction

A proof-of-concept pipeline that transcribes **handwritten student scripts** (PDF or
image) into structured, reviewable OCR output — preserving the original visual
evidence: cancelled text, caret insertions, highlights, spelling errors,
punctuation, and paragraph structure.

This is a **POC**: no auth, no hardening, optimized for readability and
iteration speed. The full technical specification lives at `.resource/specs.md`
(v1.0), with capability specs under `openspec/specs/`.

## Core principle

**Transcription fidelity over contextual correctness.** The system never
autocorrects spelling, fixes grammar, normalizes punctuation, rewrites
sentences, or drops cancelled/inserted/highlighted text. Every artifact —
original image, crops, masks, OCR results, spatial coordinates, confidence
scores — is retained in storage.

## Architecture

```
PDF / image upload
      │
      ▼
backend/ (Python: OpenCV + TrOCR + FastAPI)
  ingest → normalize → detect (questions/answers/paragraphs)
        → detect markup (highlights/strikethroughs/carets)
        → generate crops → TrOCR line OCR → reconstruct JSON
      │
      ▼
REST API (state machine: UPLOADED → … → REVIEW_REQUIRED → APPROVED → EXPORTED)
      │
      ▼
apps/web (Next.js review frontend) ←→ packages/types (shared TS contract)
```

### Backend (`backend/`)

Stage-per-module Python pipeline; `pipeline.py` is a short orchestrator,
shared structures live in `schemas.py` (mirrored by `packages/types`), and all
thresholds/weights live in `config.py` + `config.yaml`. See
[backend/README.md](backend/README.md) for the module map.

| Stage | Module |
| --- | --- |
| PDF → per-page rendered images | `pdf_to_pages.py` |
| Image preprocessing (grayscale → morphology) | `normalize_image.py` |
| Question detection + line grouping | `detect_questions.py` |
| Answer region detection | `detect_answers.py` |
| Paragraph boundary detection/splitting | `detect_paragraphs.py` |
| Line/word segmentation helpers | `opencv_analysis.py` |
| Highlight / strikethrough / caret detection | `detect_highlights.py`, `detect_strikethroughs.py`, `detect_carets.py` |
| Persist all crops + metadata before OCR | `crop_generator.py` |
| TrOCR over line crops (literal text only) | `run_trocr.py` |
| OCR + spatial + markup → final JSON | `reconstruct.py` |
| Optional gated LLM ambiguity review | `llm_review.py` (disabled by default) |
| Review state machine / corrections / export | `state_machine.py`, `review.py` |
| FastAPI endpoints | `api.py` |
| Artifact storage layout | `storage.py` |

### Frontend (`apps/web`)

Next.js 15 / React 19 review UI: zoom/pan page viewer with toggleable SVG
overlays (questions, answers, paragraphs, markup), a crop inspector for
per-crop corrections, and the paragraph tree with applied corrections. Talks
to the backend API through `apps/web/lib/api.ts` (base URL via
`NEXT_PUBLIC_API_BASE`, default `http://localhost:8000`).

### Shared types (`packages/types`)

TypeScript contract mirroring the backend JSON schemas, consumed by the web
app so frontend and backend stay in lockstep.

## Repository layout

```
backend/           Python pipeline + FastAPI (outside the turbo workspace by design)
apps/web/          Next.js review frontend (@moe-research/web)
packages/types/    Shared TS contract (@moe-research/types)
openspec/          Spec-driven workflow: capability specs + archived change
data/              Sample input documents
storage/           Pipeline artifacts per document (gitignored)
.resource/         Technical specification (specs.md, gitignored)
```

## Getting started

### Prerequisites

- Python 3.12+
- Node.js with pnpm (packageManager pinned to pnpm 11.12.0)
- TrOCR (`microsoft/trocr-large-handwritten`) is downloaded on first OCR run

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn api:app --reload        # serves on http://localhost:8000
```

### Frontend + workspace

```bash
pnpm install
pnpm run dev                    # turbo dev: Next.js on http://localhost:3000
```

Other root scripts: `pnpm run build`, `pnpm run lint`, `pnpm run check-types`,
`pnpm run test`.

### Try it

Upload a sample script through the web UI, or hit the API directly:

```bash
curl -F "file=@data/ocr-assessment-sample.pdf" http://localhost:8000/documents
```

The upload runs the full pipeline to `REVIEW_REQUIRED`, then the review UI is
used to inspect crops, submit corrections, and approve/export the final JSON.

## API overview

| Method & path | Purpose |
| --- | --- |
| `POST /documents` | Upload (multipart `file`) → runs pipeline, returns `documentId` |
| `GET /documents/{id}` | Document state + full structured JSON |
| `GET /documents/{id}/artifacts/{path}` | Serve originals / rendered pages / crops / masks / OCR artifacts |
| `POST /documents/{id}/corrections` | Submit a manual correction (`cropId`, `correctedText`, optional `reason`) |
| `POST /documents/{id}/approve` | Approve + export final JSON |

State transitions are validated by the state machine:

```
UPLOADED → NORMALIZED → QUESTION_DETECTED → ANSWER_DETECTED →
PARAGRAPHS_DETECTED → CROPS_GENERATED → OCR_PROCESSING →
MARKUP_RECONSTRUCTION → REVIEW_REQUIRED → APPROVED → EXPORTED
```

## Configuration

All pipeline thresholds, weights, and epsilons live in `backend/config.yaml`
(named defaults in `backend/config.py`): paragraph boundary scoring, question
grouping, answer trimming, highlight HSV window, strikethrough geometry, caret
symbol/insertion windows, OCR decoding, confidence routing (≥ 0.90 accepted,
0.70–0.89 review recommended, < 0.70 review required), LLM review gating,
preprocessing, and segmentation. Storage root and ingestion DPI are also
configured there.

LLM ambiguity review is **off by default** (`llm_review.enabled: false`); it
batches flagged items per page, caps calls per page, and caches by crop +
candidate hash.

## Spec-driven development

The project uses [OpenSpec](https://github.com/Fission-AI/OpenSpec). Capability
specs live under `openspec/specs/` (document-ingestion, spatial-detection,
markup-detection, crop-management, ocr-transcription, markup-reconstruction,
pipeline-orchestration, human-review, llm-ambiguity-review, review-frontend),
and the completed `handwritten-script-ocr` change is archived under
`openspec/changes/archive/`.
