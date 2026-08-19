# moe-assignment-demo — Handwritten Student Script OCR & Reconstruction

A proof-of-concept pipeline that transcribes **handwritten student scripts** (PDF or
image) into structured, reviewable OCR output — preserving the original visual
evidence: line crops, highlights, spelling errors, punctuation, and paragraph
structure.

This is a **POC**: no auth, no hardening, optimized for readability and
iteration speed. The full technical specification lives at `.resource/specs.md`
(v1.0), with capability specs under `openspec/specs/`.

## Core principle

**Transcription fidelity over contextual correctness.** The system never
autocorrects spelling, fixes grammar, normalizes punctuation, or rewrites
sentences. Every artifact —
original image, crops, masks, OCR results, spatial coordinates, confidence
scores — is retained in storage.

## Architecture

```
PDF / image upload
      │
      ▼
apps/backend/ (Python: OpenCV + OpenAI Vision LLM + FastAPI)
  ingest → normalize → detect (questions/answers/paragraphs/highlights)
        → generate immutable line crops → OpenAI Vision line OCR
        → reconstruct JSON from lines
      │
      ▼
REST API (state machine: UPLOADED → … → REVIEW_REQUIRED → APPROVED → EXPORTED)
      │
      ▼
apps/frontend (Next.js review frontend)
```

### Backend (`apps/backend/`)

Stage-per-module Python pipeline packaged under `app/`; `app/pipeline.py` is
the short orchestrator, shared structures live in `app/schemas.py`, and all
thresholds/weights live in `app/config.py` + `app/config.yaml`. See
[apps/backend/README.md](apps/backend/README.md) for the module map.

| Stage | Module |
| --- | --- |
| PDF → per-page rendered images | `app/ingest/pages.py` |
| Image preprocessing (grayscale → morphology) | `app/imaging/normalize_image.py` |
| Question detection + line grouping | `app/detect/questions.py` |
| Answer region detection | `app/detect/answers.py` |
| Paragraph boundary detection/splitting | `app/detect/paragraphs.py` |
| Line/word segmentation helpers | `app/imaging/opencv_analysis.py` |
| Highlight detection | `app/detect/highlights.py` |
| Persist all crops + metadata before OCR | `app/imaging/crop_generator.py` |
| OpenAI Vision over line crops (literal structured results) | `app/ocr/vision_llm.py` |
| Line OCR → final JSON | `app/ocr/reconstruct.py` |
| Review state machine / corrections / export | `app/state_machine.py`, `app/review.py` |
| FastAPI endpoints | `app/api.py` |
| Artifact storage layout | `app/storage.py` |

### Frontend (`apps/frontend`)

Next.js 15 / React 19 review UI (`@moe-assignment-demo/web`): a document
viewer/upload flow (`app/page.tsx`) and a review page (`app/review`) with
per-crop corrections and approval. Talks to the backend API via the
`NEXT_PUBLIC_API_BASE` env var (default `http://localhost:8000`).

## Repository layout

```
apps/backend/      Python pipeline + FastAPI (@moe-assignment-demo/backend, uv-managed)
apps/frontend/      Next.js review frontend (@moe-assignment-demo/web)
openspec/           Spec-driven workflow: capability specs + archived change
apps/backend/storage/  Pipeline artifacts per document (gitignored)
```

## Getting started

### Prerequisites

- Python 3.10+ and [uv](https://docs.astral.sh/uv/)
- Node.js with pnpm (packageManager pinned to pnpm 11.12.0)

### Backend

```bash
cd apps/backend
uv sync
uv run uvicorn app.api:app --reload   # serves on http://localhost:8000
```

Or via the root workspace: `pnpm --filter @moe-assignment-demo/backend dev`.

### Frontend + workspace

```bash
pnpm install
pnpm run dev                    # runs dev in every workspace package (frontend + backend)
```

Other root scripts: `pnpm run build`, `pnpm run lint`, `pnpm run check-types`,
`pnpm run test`.

### Try it

Upload a script (PDF or image) through the web UI (`http://localhost:3000`),
or hit the API directly:

```bash
curl -F "file=@/path/to/script.pdf" http://localhost:8000/documents
```

The upload runs the full pipeline to `REVIEW_REQUIRED`, then the review UI is
used to inspect crops, submit corrections, and approve/export the final JSON.

## API overview

| Method & path | Purpose |
| --- | --- |
| `POST /documents` | Upload (multipart `file`) → runs pipeline, returns `documentId` |
| `GET /documents/{id}/progress` | Poll pipeline progress while processing |
| `GET /documents/{id}` | Document state + full structured JSON |
| `GET /documents/{id}/artifacts/{path}` | Serve originals / rendered pages / crops / masks / OCR artifacts |
| `POST /documents/{id}/corrections` | Submit a manual correction (`cropId`, `correctedText`, optional `reason`) |
| `POST /documents/{id}/review-decisions` | Submit a review decision on an ambiguous item |
| `POST /documents/{id}/approve` | Approve + export final JSON |

State transitions are validated by the state machine:

```
UPLOADED → NORMALIZED → QUESTION_DETECTED → ANSWER_DETECTED →
PARAGRAPHS_DETECTED → CROPS_GENERATED → OCR_PROCESSING →
MARKUP_RECONSTRUCTION → REVIEW_REQUIRED → APPROVED → EXPORTED
```

## Configuration

All pipeline thresholds, weights, and epsilons live in
`apps/backend/app/config.yaml` (named defaults in `apps/backend/app/config.py`):
paragraph boundary scoring, question grouping, answer trimming, highlight HSV
window, OCR decoding, confidence routing (≥ 0.90 accepted, 0.70–0.89 review
recommended, < 0.70 review required), preprocessing, and segmentation.
Storage root and ingestion DPI are also configured there.

Vision LLM transcription uses OpenAI (`provider: openai`,
`model: gpt-5.4-mini`) through the Responses API. Copy
`apps/backend/.env.example` to `apps/backend/.env` and set `OPENAI_API_KEY`.
A repository-root `.env` is also supported; the backend loads either location
automatically. Reprocessing must reuse the already persisted immutable crop
paths; crop writes intentionally refuse overwrites. Prior crops and OCR
provenance remain available for review.

Provider evaluation metrics (cost, latency, uncertainty rate, and reviewer
acceptance) must be recorded after an operator selects a provider/model and
runs a representative dataset. No provider is selected or benchmarked in this
repository, so those measurements are intentionally not fabricated.

## Spec-driven development

The project uses [OpenSpec](https://github.com/Fission-AI/OpenSpec). Capability
specs live under `openspec/specs/` (document-ingestion, spatial-detection,
markup-detection, crop-management, ocr-transcription, markup-reconstruction,
pipeline-orchestration, human-review, llm-ambiguity-review, review-frontend),
and the completed `handwritten-script-ocr` change is archived under
`openspec/changes/archive/`.
