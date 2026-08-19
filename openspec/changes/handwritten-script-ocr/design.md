# Design: Handwritten Student Script OCR & Reconstruction

## Context

Greenfield POC/MVP build in an empty monorepo (see proposal.md for motivation). The authoritative behavioral source is `specs.md` at the repo root (spec v1.0); the delta specs in `specs/` capture the testable contract. Constraints shaping this design:

- POC only: no security, auth, or production hardening. Optimize for readability and iteration speed.
- Fidelity is the hard requirement: the image is the source of truth; OCR is interpretation, never replacement. Every text fragment must trace back to a crop.
- Tech stack is fixed by the spec: Python/FastAPI/OpenCV/PyTorch/Transformers(TrOCR)/Pillow/PyMuPDF backend; Next.js/TypeScript frontend with SVG overlays; Turborepo + pnpm workspaces with the Python backend outside turbo.

## Goals / Non-Goals

**Goals:**
- A stage-per-module Python pipeline where each stage is a pure function over shared schema types, wired by one short orchestrator.
- Immutable crop layer as the seam between spatial analysis (OpenCV) and transcription (TrOCR), enabling model swaps without re-segmentation.
- One JSON contract shared between backend and frontend via `packages/types`.
- All thresholds/weights/epsilons configurable; all intermediate artifacts retained.

**Non-Goals:**
- Security, authentication, multi-user, deployment hardening, horizontal scaling.
- Any text correction (spelling/grammar/punctuation/translation) — architecturally forbidden, not just discouraged.
- Training or fine-tuning OCR models; we consume pretrained TrOCR.
- Phase 3 items beyond what the specs already capture (model comparison tooling, OCR retry pipeline) — out of this change.

## Decisions

### 1. Two-engine architecture with crops as the contract
OpenCV determines *where*; TrOCR determines *what*; a reconstruction engine decides *how markup is represented*; a human decides *acceptable*. All cross-engine communication happens through persisted crops + JSON metadata — never in-memory image mutations.
Alternatives considered: end-to-end vision-LLM transcription (rejected: no crop traceability, invites autocorrection, violates the fidelity contract); OCR-first-then-layout (rejected: text normalization tends to destroy spatial evidence before it can be recorded).

### 2. Crops persisted before OCR, immutable thereafter
`crop_generator` runs to completion and writes every crop (question/answer/paragraph/line/word/cancelled/caret) with metadata before any TrOCR call. OCR results reference crops by `cropId` only. This makes OCR re-runs cheap and comparable across models.
Alternatives: lazy/on-demand cropping (rejected: re-segmentation cost on model swap, risk of drift between runs).

### 3. Pipeline = ordered pure-function stages over a document context object
Each stage is one file named after its responsibility (`pdf_to_pages.py`, `normalize_image.py`, `detect_questions.py`, `detect_answers.py`, `detect_paragraphs.py`, `opencv_analysis.py`, `detect_highlights.py`, `detect_strikethroughs.py`, `detect_carets.py`, `crop_generator.py`, `run_trocr.py`, `reconstruct.py`, `llm_review.py`). `pipeline.py` calls them in order and advances the state machine. Shared structures live in `backend/schemas.py` (mirrored by `packages/types`).
Alternatives: class-based stage hierarchy (rejected by the readability rules: plain functions, no clever abstractions).

### 4. Detection ordering: question → answer → paragraph → markup, all before OCR
Question detection anchors the page structure; the answer bbox is derived relative to it; paragraph splitting happens inside the answer region before any detailed OCR, so each paragraph is OCR'd independently. Markup detection (highlights/strikethrough/carets) runs on the spatial side and attaches as metadata — it never feeds back into OCR input.

### 5. Paragraph boundary detection as a configurable weighted score
Primary signal: vertical gap (`gap = next_line.y - (current_line.y + current_line.height)`). Secondary: indentation, blank lines, density, horizontal start, line spacing, paragraph length. Conceptual score `0.55*gap + 0.25*indent + 0.20*density` with all weights as config constants, tuned against `data/ocr-assessment-sample.png` during the POC.
Alternatives: fixed-gap-only heuristic (rejected: too brittle on real handwriting), learned paragraph model (rejected: POC scope).

### 6. Deterministic-first caret anchoring, LLM as gated tie-breaker
Anchor = caret tip x projected onto the anchor line, snapped to nearest inter-word gap. Only when ambiguous (two gaps within `gap_epsilon_px`, caret inside a word bbox, clustered/orphan carets, low anchor-line confidence, unclear line assignment) is the LLM asked — and only as multiple choice over numbered tick marks rendered onto the anchor-line crop. Invalid indices are rejected and fall back to the deterministic guess + human flag.

### 7. LLM low-confidence review selects among TrOCR N-best candidates
TrOCR runs with beam search to produce N-best candidates; the LLM picks an index. Because all candidates come from actual ink, structural autocorrect is impossible by construction. Free-form transcription exists only as a documented fallback and is character-diff-validated against top-1, rejected on signs of normalization. Stage is `enabled: false` by default; when disabled, code path is a no-op so behavior is bit-identical. All suggestions attach with `applied: false`.

### 8. FastAPI exposes documents, status, artifacts, and review actions
Endpoints: upload document; get document state/JSON; serve original/rendered/crop images; list/update review corrections; approve/export. No auth (POC). State transitions are validated against the state machine in `pipeline-orchestration`.

### 9. Frontend: SVG overlays in original-image coordinates + crop inspector
Next.js app renders the rendered page image and draws bboxes/polygons as SVG in the same coordinate system (no client-side scaling math beyond viewBox). Overlay toggles, paragraph tree navigation, crop inspector panel (location → crop → OCR result → reconstructed text), confidence flagging, and a text editor for corrections. Types come exclusively from `packages/types`.

### 10. Storage layout mirrors the spec exactly
`storage/{originals,rendered,processed/<page>,crops/<page>/<type>,ocr/<page>,output}`. Written by the stage that produces each artifact; paths recorded in metadata. Filesystem is the POC database — document JSON is the record of truth per document.

## Risks / Trade-offs

- [Handwriting variance breaks spatial heuristics (dense/slanted/cramped scripts)] → All thresholds configurable; retain every intermediate artifact so failures are debuggable against the sample data; accept imperfect segmentation in POC and rely on human review as the backstop.
- [TrOCR accuracy on real student handwriting may be low] → Confidence flagging + N-best candidates + optional LLM selection + mandatory human review; crop immutability lets us swap in better models without re-segmentation.
- [Caret/strikethrough detection is genuinely hard CV] → Deterministic-first rules keep behavior predictable; ambiguous cases escalate to LLM multiple-choice then human — never silent guessing.
- [LLM responses are unreliable] → Strict JSON contracts, index validation against rendered candidates, diff validation for fallbacks, per-page call cap, caching, `applied: false` until human confirms — worst case degrades to deterministic + human.
- [Schema drift between Python backend and TS frontend] → `packages/types` is the single contract; any JSON shape change must land there first.
- [POC filesystem storage has no transactionality] → Acceptable for POC; pipeline is idempotent per stage and re-runnable because crops are immutable.

## Migration Plan

Greenfield — no migration. Rollout: build backend pipeline stages → validate against `data/ocr-assessment-sample.png` → add API + frontend review loop → enable optional LLM stage behind config for evaluation. Rollback = disable LLM review config flag or run pipeline stages individually (each is a standalone module).

## Open Questions

- Which vision-capable LLM model to configure for the optional review stage (only matters when `llm_review.enabled: true`).
- Exact paragraph-scoring weight values — defaults from the spec (0.55/0.25/0.20), tuned empirically during POC testing.
