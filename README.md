# Handwritten OCR & Reconstruction

A proof-of-concept pipeline that transcribes **handwritten student scripts** (PDF or
image) into structured, reviewable OCR output — preserving the original visual
evidence: line crops, highlights, spelling errors, punctuation, and paragraph
structure.

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
REST API (state machine: UPLOADED → … → MARKUP_RECONSTRUCTION → REVIEW_REQUIRED)
      │
      ▼
apps/frontend (Next.js review frontend)
```

See [API overview](#api-overview) for the REST endpoints and full state
machine transitions.

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
| Vision LLM over line crops (literal structured results) | `app/ocr/vision_llm.py`, `app/ocr/providers/` |
| Line OCR → final JSON | `app/ocr/reconstruct.py` |
| Review state machine / low-confidence flagging | `app/state_machine.py`, `app/review.py` |
| FastAPI endpoints | `app/api.py` |
| Artifact storage layout | `app/storage.py` |

### Frontend (`apps/frontend`)

Next.js 15 / React 19 review UI (`@moe-assignment-demo/web`): a document
viewer/upload flow (`app/page.tsx`) and a review page (`app/review`) for
inspecting crops and OCR results. Talks to the backend API via the
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

### Testing the pipeline

Upload a script (PDF or image) through the web UI (`http://localhost:3000`),
or hit the API directly:

```bash
curl -F "file=@/path/to/script.pdf" http://localhost:8000/documents
```

The upload runs the full pipeline to `REVIEW_REQUIRED`, then the review UI is
used to inspect crops and OCR results.

## Storage

Every retained artifact lives on disk under a per-document directory,
functioning as an append-only log of the pipeline's work, laid out by
`apps/backend/app/storage.py`:

```
storage/<documentId>/
├── originals/       uploaded PDF/image, unmodified
├── rendered/         page_NNN.png — one rendered page per PDF page
├── processed/<page>/ normalized/preprocessed page image
├── crops/<page>/      question/ answer/ paragraph/ line/ word/ — immutable line crops
├── ocr/<page>/        final OCR JSON per unit
├── llm/<page>/         one raw LLM response JSON per unit (unedited provenance)
└── output/            document.json — created on demand at export time
```

Crops are immutable once written (`write_crop` refuses to overwrite), so
reprocessing a document reuses prior crop paths rather than replacing them.
All paths are stored relative to the document root so the storage tree stays
portable. Any artifact above is retrievable by clients via
`GET /documents/{id}/artifacts/{path}` (see [API overview](#api-overview)),
which is how the review frontend fetches original scans, crops, and OCR/LLM
JSON for display.

## API overview

| Method & path | Purpose |
| --- | --- |
| `POST /documents` | Upload (multipart `file`) → runs pipeline, returns `documentId` |
| `GET /documents/{id}/progress` | Poll pipeline progress while processing |
| `GET /documents/{id}` | Document state + full structured JSON |
| `GET /documents/{id}/artifacts/{path}` | Serve originals / rendered pages / crops / masks / OCR artifacts |

State transitions are validated by the state machine. The pipeline currently
drives documents up to `REVIEW_REQUIRED`; `APPROVED`/`EXPORTED` remain
defined in `app/state_machine.py` but have no API route driving them:

```
UPLOADED → NORMALIZED → QUESTION_DETECTED → ANSWER_DETECTED →
PARAGRAPHS_DETECTED → CROPS_GENERATED → OCR_PROCESSING →
MARKUP_RECONSTRUCTION → REVIEW_REQUIRED
```

## OCR Configuration

All pipeline thresholds, weights, and epsilons live in
`apps/backend/app/config.yaml`, which overrides the named defaults in
`apps/backend/app/config.py`; missing keys fall back to those defaults.

| Section | Purpose |
| --- | --- |
| `paragraph` | Weights (vertical gap / indentation / density), gap multiple, and score threshold used to detect paragraph boundaries |
| `question` | Header height factor, max gap, and short-line ratio used to group question lines |
| `answer` | Trim density ratio, margin scribble distance, and min ink area used to detect answer regions |
| `highlight` | Yellow HSV window (hue/sat/val min-max), cleanup size, and min area used to detect highlights |
| `confidence` | Review routing thresholds: ≥ 0.90 accepted, 0.70–0.89 review recommended, < 0.70 review required |
| `vision_llm` | OCR provider/model/endpoint, API key env var, max calls per page, and response caching |
| `storage` | Storage root directory for persisted artifacts |
| `ingestion` | DPI used when rendering PDF pages to images |
| `preprocess` | Denoising, CLAHE, deskew, adaptive threshold, and morphology settings for image normalization |
| `segment` | Rule/margin kernel sizes and ink/gap tolerances used for line and word segmentation |

Reprocessing must reuse the already persisted immutable crop paths; crop
writes intentionally refuse overwrites. Prior crops and OCR provenance
remain available for review.

## Vision LLM

Line transcription is provider-swappable, configured under `vision_llm` in
`apps/backend/app/config.yaml`. Set `provider` to `openai` or `openrouter`;
`apps/backend/app/config.yaml` has commented example blocks for each, and
both dispatch through the same shared transcription prompt at
`apps/backend/app/ocr/prompts/line_transcription.md`. Models tested:
`gpt-5.4-mini` (OpenAI) and `qwen/qwen3-vl-8b-instruct` (OpenRouter).

Copy `apps/backend/.env.example` to `apps/backend/.env` and set the API key
env var for whichever provider you choose. A repository-root `.env` is also
supported; the backend loads either location automatically.

| Setting | Purpose |
| --- | --- |
| `provider` | `openai` \| `openrouter` — dispatches to the matching module in `app/ocr/providers/` |
| `model` | Vision model used for line OCR (provider-specific slug) |
| `endpoint` | API endpoint for the selected provider |
| `api_key_env` | Env var name holding that provider's API key |
| `max_calls_per_page` | Cap on Vision API calls per page |
| `cache` | Whether raw LLM responses are cached/reused |



### Logging

Every outgoing request and incoming response for both providers is
logged by `app/ocr/providers/_shared.py:post_json` (image bytes and any
string over 300 chars are truncated before logging, so API keys and image
payloads never hit disk in full). Logs are written to
`apps/backend/logs/llm.log` (LLM traffic only, rotates at 10MB × 5 files)
and also to `apps/backend/logs/app.log` (all app logging) plus the console.
HTTP errors log the provider's actual response body — previously these were
swallowed into a bare `provider_failure:HTTPError` reason with no way to see
why a call failed; the full body and exception now reach `logs/llm.log`.
`logs/` is gitignored.

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
