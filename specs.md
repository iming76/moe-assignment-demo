# Handwritten Student Script OCR & Reconstruction

## Technical Specification

**Version:** 1.0
**Status:** POC / MVP
**Build Nature:** POC only — no security, authentication, hardening, or production readiness is required. Optimized for readability and iteration speed.
**Primary Goal:** High-fidelity transcription of handwritten student scripts while preserving the original visual evidence, including cancelled text, caret insertions, highlights, spelling errors, punctuation, and paragraph structure.

---

# 1. Overview

The system accepts student scripts in **PDF or image format** and converts them into structured, reviewable OCR output.

The system must prioritize **transcription fidelity over contextual correctness**.

The system must not:

* autocorrect spelling
* correct grammar
* normalize punctuation
* rewrite sentences
* remove cancelled text
* remove inserted text
* discard highlighted regions
* merge separate paragraphs incorrectly
* preserve physical line breaks as paragraph breaks

The system must preserve:

* original image
* question
* answer
* paragraph structure
* line structure
* highlighted regions
* cancelled regions
* caret symbols
* inserted text
* OCR crops
* OCR results
* spatial coordinates
* confidence scores

---

# 2. Core Principle

The system follows this principle:

> **The image is the source of truth. OCR is an interpretation of the image, not a replacement for it.**

Therefore:

```text
Original Image
      │
      ├── Spatial information
      │      ├── Question
      │      ├── Answer
      │      ├── Paragraphs
      │      ├── Lines
      │      ├── Highlights
      │      ├── Strikethrough
      │      └── Carets
      │
      └── OCR crops
             │
             └── TrOCR → literal text
```

Every extracted text fragment must be traceable back to an image crop.

---

# 3. Supported Input

## 3.1 Image

Supported formats:

* PNG
* JPG
* JPEG
* WEBP

## 3.2 PDF

Supported:

* scanned PDF
* image-based PDF
* multi-page PDF

The PDF must first be rendered into page images.

```text
document.pdf
    │
    ├── page_001.png
    ├── page_002.png
    └── page_003.png
```

The original PDF must remain unchanged.

---

# 4. Processing Pipeline

```text
Upload
  │
  ▼
Document Normalization
  │
  ▼
Page Rendering
  │
  ▼
Question Detection
  │
  ▼
Answer Detection
  │
  ▼
Paragraph Detection
  │
  ├── 1 paragraph ──────────────┐
  │                             │
  └── Multiple paragraphs       │
          │                     │
          ▼                     │
    Split paragraphs            │
          │                     │
          └──────────┬──────────┘
                     ▼
             OpenCV Analysis
                     │
                     ▼
               Crop Generator
                     │
                     ▼
             Persist All Crops
                     │
                     ▼
                  TrOCR
                     │
                     ▼
          Markup Reconstruction
                     │
                     ▼
              Final JSON
                     │
                     ▼
             Frontend Review
                     │
                     ▼
                 Approved
```

---

# 5. Processing Stages

## 5.1 Document Normalization

Convert all input formats into a common internal representation.

```typescript
interface PageImage {
  pageNumber: number;
  path: string;
  width: number;
  height: number;
  dpi: number;
}
```

For image input:

```text
image → PageImage
```

For PDF:

```text
PDF → PageImage[]
```

---

# 6. Original Image Preservation

The original uploaded file must never be modified.

Storage:

```text
storage/
├── originals/
│   ├── document.pdf
│   └── page_001.png
│
└── rendered/
    ├── page_001.png
    └── page_002.png
```

All bounding boxes must use the dimensions of the rendered page image as the coordinate system.

---

# 7. Question Detection

The system must detect the question before processing the answer.

Typical question indicators:

```text
Q1
Q2
QN 1
Question
Question 1
```

Additional signals:

* question mark
* question-like sentence
* position near the top of the answer area
* larger gap after question
* answer handwriting following the question

Example:

```text
QN 1: What are the advantages and disadvantages of teens using
social media in communicating with others?
```

This is one question even though it occupies two physical lines.

---

# 8. Question Line Grouping

Physical lines belonging to the same question must be merged.

Input:

```text
QN 1: What are the advantages and disadvantages of teens using
social media in communicating with others?
```

Output:

```text
QN 1: What are the advantages and disadvantages of teens using social media in communicating with others?
```

Physical line breaks must not appear in the final question.

---

# 9. Question Data Model

```typescript
interface Question {
  id: string;

  bbox: BoundingBox;

  cropPath: string;

  lines: string[];

  text: string;

  confidence?: number;
}
```

Example:

```json
{
  "id": "q001",
  "bbox": {
    "x": 120,
    "y": 240,
    "width": 850,
    "height": 70
  },
  "cropPath": "crops/questions/q001.png",
  "text": "QN 1: What are the advantages and disadvantages of teens using social media in communicating with others?"
}
```

---

# 10. Answer Detection

After detecting the question, the system must determine the answer region.

```text
Page
 │
 ├── Header
 │
 ├── Question
 │
 └── Answer
```

The answer starts after the question region and associated spacing.

Answer detection should use:

* vertical position
* blank-line spacing
* handwriting density
* question bounding box
* line grouping
* indentation

The answer region must be stored as a bounding box.

---

# 11. Paragraph Detection

Paragraph detection occurs **before detailed OCR**.

The system must distinguish:

```text
physical line
```

from:

```text
logical paragraph
```

Example:

```text
Line 1
Line 2
Line 3
Line 4
Line 5
```

may represent:

```text
Paragraph 1
```

---

# 12. Paragraph Boundary Detection

Paragraph boundaries should be detected using multiple spatial signals.

### Primary signal

Vertical gap between handwriting lines.

```python
gap = next_line.y - (current_line.y + current_line.height)
```

### Secondary signals

* indentation
* blank line
* handwriting density
* horizontal starting position
* line spacing
* paragraph length

Conceptually:

```python
paragraph_score = (
    vertical_gap_score * 0.55 +
    indentation_score * 0.25 +
    density_score * 0.20
)
```

The exact weights are configurable.

---

# 13. Paragraph Splitting

### One paragraph

```text
Question
    ↓
Answer
    ↓
Paragraph 1
    ↓
OCR
```

### Multiple paragraphs

```text
Question
    ↓
Answer
    ↓
Paragraph detection
    ↓
Paragraph 1
Paragraph 2
Paragraph 3
    ↓
OCR independently
```

Each paragraph must have its own image crop.

---

# 14. Paragraph Data Model

```typescript
interface Paragraph {
  id: string;

  pageNumber: number;

  order: number;

  bbox: BoundingBox;

  cropPath: string;

  lines: OCRLine[];

  highlights: Highlight[];

  markups: Markup[];

  text: string;
}
```

---

# 15. OpenCV Processing

OpenCV is responsible for spatial/image processing.

It must not be responsible for correcting text.

Responsibilities:

* grayscale conversion
* denoising
* contrast normalization
* deskewing
* thresholding
* horizontal line detection
* handwriting region detection
* contour detection
* connected components
* highlight detection
* strikethrough detection
* caret detection
* crop generation

---

# 16. Image Preprocessing

Recommended pipeline:

```text
Original
   ↓
Grayscale
   ↓
Denoise
   ↓
Contrast normalization
   ↓
Deskew
   ↓
Binary / adaptive threshold
   ↓
Morphological processing
   ↓
Line detection
```

The processed images are intermediate artifacts only.

The original image must remain available.

---

# 17. Highlight Detection

Highlights must be detected independently from OCR.

For yellow highlights:

```text
RGB
 ↓
HSV
 ↓
Yellow mask
 ↓
Morphological cleanup
 ↓
Contours
 ↓
Highlight polygons
```

Example:

```json
{
  "id": "highlight_001",
  "type": "highlight",
  "bbox": {
    "x": 780,
    "y": 154,
    "width": 130,
    "height": 49
  },
  "polygon": [
    { "x": 780, "y": 154 },
    { "x": 910, "y": 154 },
    { "x": 910, "y": 203 },
    { "x": 780, "y": 203 }
  ]
}
```

Highlight detection must not alter OCR text.

---

# 18. Strikethrough Detection

Cancelled text must be preserved.

The system should identify strokes that cross handwriting.

Detection signals:

* long diagonal/horizontal strokes
* intersection with handwriting
* stroke orientation
* stroke length
* overlap with text region

The detected region should be associated with the corresponding OCR text span.

Example:

```html
<strikethrough>five hundred</strikethrough>
```

The cancelled text must remain in the output.

---

# 19. Caret Detection

Caret insertions must be detected spatially.

Typical caret:

```text
    inserted text
         ↓
       \   /
        \ /
---------^---------
```

The system must detect:

1. caret symbol
2. inserted text above/near the caret
3. anchor position in the original line

Example:

```json
{
  "id": "caret_001",
  "type": "caret",
  "caret": {
    "bbox": {
      "x": 850,
      "y": 173,
      "width": 20,
      "height": 12
    }
  },
  "insertCrop": "crops/carets/caret_001.png",
  "anchorLineId": "p003_line004"
}
```

---

# 20. Crop Generation

All crops must be saved **before TrOCR**.

Required crop types:

```text
question
answer
paragraph
line
word
cancelled
caret
```

Recommended storage:

```text
crops/
├── questions/
├── answers/
├── paragraphs/
├── lines/
├── words/
├── cancelled/
└── carets/
```

---

# 21. Crop Immutability

Once a crop has been generated, it must not be modified.

This allows:

```text
Original crop
     ↓
TrOCR model A
     ↓
TrOCR model B
     ↓
Improved OCR model
```

without repeating segmentation.

---

# 22. Crop Metadata

Every crop must have metadata.

```typescript
interface Crop {
  id: string;

  type:
    | "question"
    | "answer"
    | "paragraph"
    | "line"
    | "word"
    | "cancelled"
    | "caret";

  pageNumber: number;

  parentId?: string;

  path: string;

  bbox: BoundingBox;

  createdAt: string;
}
```

Example:

```json
{
  "id": "p002_line004",
  "type": "line",
  "parentId": "p002",
  "pageNumber": 1,
  "path": "crops/lines/p002_line004.png",
  "bbox": {
    "x": 120,
    "y": 740,
    "width": 880,
    "height": 42
  }
}
```

---

# 23. TrOCR

TrOCR must operate primarily on **line-level crops**.

```text
line crop
    ↓
TrOCR
    ↓
literal OCR text
```

TrOCR must not receive responsibility for:

* paragraph detection
* question detection
* spelling correction
* grammar correction
* caret reconstruction
* strike reconstruction

---

# 24. OCR Result

```typescript
interface OCRResult {
  cropId: string;

  text: string;

  confidence: number;

  tokens?: OCRToken[];

  processingTimeMs?: number;

  model: string;
}
```

Example:

```json
{
  "cropId": "p002_line004",
  "text": "my mother used to tell me stories of how",
  "confidence": 0.94,
  "model": "microsoft/trocr-base-handwritten"
}
```

---

# 25. OCR Fidelity Rules

The OCR/reconstruction engine MUST preserve:

### Spelling

```text
teens
```

must remain:

```text
teens
```

even if the model thinks it should be something else.

### Grammar

Do not change:

```text
more and more people start to use it
```

into:

```text
more and more people started using it
```

### Punctuation

Do not normalize:

```text
However ,
```

into:

```text
However,
```

unless the original handwriting clearly indicates the latter.

### Language

Do not translate.

### Capitalization

Preserve the student's capitalization.

---

# 26. Reconstruction Engine

The reconstruction engine combines:

```text
OCR
+
spatial metadata
+
markup metadata
```

to produce final text.

Example:

```text
OCR:
She had to walk five hundred kilometres.

Markup:
"five hundred" = cancelled
"two" = caret insertion

Final:
She had to walk <strikethrough>five hundred</strikethrough> <caret>two</caret> kilometres.
```

---

# 27. Caret Reconstruction

Caret text must be inserted into its logical position.

Example:

```text
Original OCR:

send a text message to their classmate

Caret insertion:

          ^
     in seconds
```

Final:

```html
send a text <caret>in seconds</caret> message to their classmate
```

The system must not simply append the inserted text to the end of the paragraph.

---

# 28. Strikethrough Reconstruction

Example:

```html
The candidate felt <strikethrough>nervous</strikethrough> excited.
```

Cancelled text remains visible in the transcription.

---

# 29. Paragraph Formatting

Physical handwriting line breaks must not appear in final text.

Input:

```text
Line 1
Line 2
Line 3
```

Output:

```text
Line 1 Line 2 Line 3
```

Separate paragraphs must use:

```text
\n\n
```

Example:

```text
Paragraph one.

Paragraph two.

Paragraph three.
```

---

# 30. Final Output

The final output should contain:

```json
{
  "question": "...",
  "answer": "Paragraph one...\n\nParagraph two...\n\nParagraph three..."
}
```

The internal processing JSON contains much more information.

---

# 31. Complete Internal JSON

```json
{
  "documentId": "doc_001",

  "source": {
    "type": "pdf",
    "originalPath": "originals/doc_001.pdf"
  },

  "pages": [
    {
      "pageNumber": 1,

      "image": {
        "path": "rendered/page_001.png",
        "width": 1024,
        "height": 1280
      },

      "question": {
        "id": "q001",
        "cropPath": "crops/questions/q001.png",
        "bbox": {},
        "text": "QN 1: What are the advantages and disadvantages of teens using social media in communicating with others?"
      },

      "answer": {
        "bbox": {},

        "paragraphs": [
          {
            "id": "p001",
            "order": 1,
            "cropPath": "crops/paragraphs/p001.png",

            "lines": [],

            "highlights": [],

            "markups": [],

            "text": "..."
          },
          {
            "id": "p002",
            "order": 2,
            "cropPath": "crops/paragraphs/p002.png",

            "lines": [],

            "highlights": [],

            "markups": [],

            "text": "..."
          }
        ]
      }
    }
  ],

  "final": {
    "question": "...",
    "answer": "Paragraph 1...\n\nParagraph 2..."
  }
}
```

---

# 32. Frontend Requirements

The frontend must show the original image as the primary visual source.

Required functionality:

### Image viewer

* zoom
* pan
* page navigation
* original resolution
* overlay toggle

### Overlay types

```text
☑ Question
☑ Answer
☑ Paragraphs
☑ Lines
☑ Highlights
☑ Strikethrough
☑ Carets
```

### Crop inspector

When a user clicks an object:

```text
Original location
       ↓
Corresponding crop
       ↓
TrOCR result
       ↓
Final reconstructed text
```

---

# 33. Frontend Paragraph Navigation

The user should be able to select:

```text
Question
 └── Answer
      ├── Paragraph 1
      ├── Paragraph 2
      └── Paragraph 3
```

Selecting a paragraph should:

1. highlight its bounding box on the original page
2. display the paragraph crop
3. display its line crops
4. display detected highlights
5. display cancelled text
6. display caret insertions
7. display OCR confidence
8. allow manual correction

---

# 34. Human Review

The system should have a review state.

```text
OCR Complete
     ↓
Review Required
     ↓
Human Review
     ↓
Approve
```

Low-confidence regions should be automatically flagged.

Example:

```json
{
  "cropId": "p003_line005",
  "confidence": 0.54,
  "reviewRequired": true
}
```

---

# 35. Low Confidence Rules

Configurable default:

```text
confidence >= 0.90
    → accepted

0.70 - 0.89
    → review recommended

< 0.70
    → review required
```

These thresholds must be configurable.

---

# 36. Processing Artifacts

The system should retain:

```text
Original
Rendered page
Deskewed image
Binary image
Highlight mask
Line segmentation image
Paragraph crops
Line crops
Word crops
Caret crops
Cancelled crops
OCR JSON
Final JSON
```

This is important for debugging and model improvement.

---

# 37. Recommended Directory Structure

```text
storage/
│
├── originals/
│   ├── document.pdf
│   └── uploaded.png
│
├── rendered/
│   ├── page_001.png
│   └── page_002.png
│
├── processed/
│   └── page_001/
│       ├── grayscale.png
│       ├── deskew.png
│       ├── binary.png
│       ├── highlight_mask.png
│       └── line_mask.png
│
├── crops/
│   └── page_001/
│       ├── questions/
│       ├── answers/
│       ├── paragraphs/
│       ├── lines/
│       ├── words/
│       ├── cancelled/
│       └── carets/
│
├── ocr/
│   └── page_001/
│       ├── q001.json
│       ├── p001.json
│       └── p002.json
│
└── output/
    └── document.json
```

---

# 38. Technology Stack

## Backend

```text
Python
FastAPI
OpenCV
PyTorch
Transformers
TrOCR
Pillow
PyMuPDF / pdf2image
```

## Frontend

```text
Next Js react
TypeScript
Canvas / SVG overlay
```

## Monorepo Tooling

```text
Turborepo
pnpm workspaces
```

Repository layout:

```text
moe-research/
├── apps/
│   └── web/          # Next.js frontend
├── packages/
│   └── types/        # shared TS types mirroring backend JSON schemas
├── backend/          # FastAPI + OpenCV + TrOCR (Python, outside turbo)
├── turbo.json
└── pnpm-workspace.yaml
```

Turborepo orchestrates build, lint, test, and dev tasks across the JS/TS workspace with caching. The backend remains Python and lives outside the turbo workspace; `packages/types` mirrors the backend JSON schemas so both sides share the same contract.

## Code Readability Requirements

This is a POC. Security and production hardening are out of scope. Code is optimized for **readability** so the pipeline can be iterated quickly.

```text
Readability rules:

* small modules, one responsibility each
  (e.g. pdf_to_pages.py, detect_questions.py, detect_carets.py, crop_generator.py, run_trocr.py, reconstruct.py, llm_review.py)
* no clever abstractions — plain functions over classes
* every pipeline stage is a separate file named after its stage
* stages are wired together in one short orchestrator file (pipeline.py)
* shared data structures live in one models file (schemas.py / packages/types)
* every function gets a docstring: what it takes in, what it returns
* magic numbers (thresholds, weights, epsilon) are named constants or config values
* no dead code, no unused branches
* prefer obvious code over compact code
```

Recommended frontend architecture:

```text
Original Image
      +
SVG Overlay
      +
Crop Inspector
      +
OCR Text Editor
```

SVG is particularly suitable for displaying bounding boxes and polygons because the coordinates can remain tied to the original image coordinate system.

---

# 39. Optional LLM Stage

An LLM may be introduced only as a **secondary ambiguity resolver**.

Allowed:

```text
OCR confidence low
+
spatial information
+
original crop
        ↓
LLM review
```

The LLM may determine:

* whether two OCR fragments belong together
* likely caret anchor
* whether a stroke is a strikethrough
* paragraph boundary ambiguity

The LLM must **not**:

* grammar-correct
* spell-correct
* rewrite
* summarize
* infer what the student intended to say

The image remains the source of truth.

---

# 39.1 LLM Ambiguity Review — Operational Design

This section defines how the optional LLM stage (Section 39) is integrated as a gated final review pass. It applies **only** to:

* ambiguous caret anchoring
* low-confidence OCR regions

The LLM stage is:

* **optional** — disabled by default; when disabled, pipeline behavior is identical
* **final** — it runs after markup reconstruction, immediately before human review
* **non-authoritative** — it produces suggestions attached to existing objects; `applied` remains false until a human reviewer confirms

The LLM never overwrites OCR text, spatial metadata, or markup.

## 39.1.1 Pipeline position

```text
MARKUP_RECONSTRUCTION
        │
        ▼
Collect ambiguity flags
        │
        ├── no flags, or LLM disabled ──────────┐
        │                                       │
        ▼                                       │
LLM_AMBIGUITY_REVIEW (optional state)           │
        │                                       │
        └───────────────┬───────────────────────┘
                        ▼
                 REVIEW_REQUIRED
                        │
                        ▼
                HUMAN REVIEW (approves everything)
```

## 39.1.2 Trigger A — ambiguous caret anchor

Deterministic rule first:

```text
anchor_x = caret tip x projected onto the anchor line
        → nearest inter-word gap on the anchor line
```

Escalate to the LLM only when the deterministic step is ambiguous:

* two candidate gaps within `gap_epsilon_px` of the projection
* the caret x falls inside a word bbox instead of a gap
* multiple carets clustered together, or a caret without associated inserted text (or vice versa)
* the anchor line OCR confidence is itself low
* inserted text lies between two lines and line assignment is unclear

The LLM request must be **multiple choice**, never open-ended:

```text
Input:
  * anchor-line crop with numbered tick marks drawn at each candidate gap
  * caret crop
  * inserted-text crop

Question:
  "Which numbered position is the insertion point?"

Required output (strict JSON):
  { "anchorIndex": 2, "confidence": 0.8, "reason": "..." }
```

Validation:

```text
anchorIndex must be one of the candidate indices rendered in the image.
Otherwise → reject the response, keep the deterministic best guess, flag for human review.
```

## 39.1.3 Trigger B — low-confidence regions

The gate reuses the Section 35 thresholds:

```text
confidence < 0.70           → send to LLM review (when enabled)
confidence 0.70 - 0.89      → only if include_review_recommended = true
confidence >= 0.90          → never sent
```

The LLM must not be asked to transcribe freely.

TrOCR must first run with beam search to produce N-best candidates for the crop. The LLM selects among the candidates:

```text
Input:
  * line/word crop
  * at most 1 context line above and below
  * N-best OCR candidates with confidences

Question:
  "Which candidate matches the handwriting in the image? Answer with the candidate index only."

Required output (strict JSON):
  { "candidateIndex": 1, "confidence": 0.72, "reason": "..." }
```

Because every candidate was produced from the actual ink, the LLM cannot introduce spelling or grammar corrections.

Free-form transcription is permitted only as a documented fallback. Its output must be validated by character diff against the TrOCR top-1 candidate, and rejected if the diff suggests normalization (punctuation spacing, capitalization, word-form changes).

## 39.1.4 Data model

```typescript
interface LLMReview {
  id: string;

  targetId: string;          // cropId or caret id
  trigger: "caret_anchor_ambiguity" | "low_confidence";

  inputs: {
    cropPaths: string[];
    candidates: string[];
  };

  rawResponse: object;

  chosen: string | number;   // candidate / anchor index chosen
  agreedWithDeterministic: boolean;
  applied: boolean;          // false until a human confirms

  model: string;
  latencyMs: number;
}
```

`llmReview?: LLMReview` is attached to `OCRResult` and to caret markup objects. Carets with ambiguous anchors additionally carry `anchorCandidates` so the frontend can render candidate tick marks in the overlay.

## 39.1.5 Request scope

Per call the LLM receives only:

```text
* the target crop (line / word / caret)
* at most 1 context line above and below (only when anchoring depends on it)
* spatial metadata (bboxes, candidate list)
* OCR candidates + confidences
* the fidelity contract (Section 25 and Section 39 constraints)
```

The full page image is never sent.

## 39.1.6 Configuration

```yaml
llm_review:
  enabled: false               # off by default
  model: vision-capable LLM
  triggers:
    caret_anchor:
      gap_epsilon_px: 8
    low_confidence:
      threshold: 0.70
      include_review_recommended: false
  batch: true                  # group all flagged items of a page into one call
  max_calls_per_page: 10
  cache: true                  # key = hash(crop bytes + candidate list)
```

## 39.1.7 Guarantees

```text
Optional      → enabled: false yields zero behavior change.
Final         → runs after reconstruction, before human review.
Scope-limited → only two trigger classes exist.
Fidelity-safe → selection among ink-derived candidates;
                the LLM cannot structurally autocorrect.
```

The system tracks how often the LLM choice differs from the deterministic result (`agreedWithDeterministic`). Near-zero disagreement → tighten the ambiguity thresholds. High disagreement → improve the deterministic caret projection.

---

# 40. Processing State Machine

```text
UPLOADED
   │
   ▼
NORMALIZED
   │
   ▼
QUESTION_DETECTED
   │
   ▼
ANSWER_DETECTED
   │
   ▼
PARAGRAPHS_DETECTED
   │
   ▼
CROPS_GENERATED
   │
   ▼
OCR_PROCESSING
   │
   ▼
MARKUP_RECONSTRUCTION
   │
   ▼
REVIEW_REQUIRED
   │
   ├── correction
   │       │
   │       └──────────────┐
   │                      │
   ▼                      │
APPROVED ◄────────────────┘
   │
   ▼
EXPORTED
```

---

# 41. MVP Scope

### Phase 1

Support:

* PNG
* JPG
* single-page PDF
* question detection
* answer detection
* paragraph detection
* line detection
* crop saving
* TrOCR
* final JSON
* original image viewer

### Phase 2

Add:

* highlight detection
* strikethrough detection
* caret detection
* crop inspector
* confidence visualization
* human review

### Phase 3

Add:

* multi-page PDF
* multiple questions per document
* automatic question/answer grouping
* LLM ambiguity resolver
* model comparison
* OCR retry pipeline

---

# 42. Acceptance Criteria

## Input

* [ ] System accepts PNG.
* [ ] System accepts JPG/JPEG.
* [ ] System accepts PDF.
* [ ] Original file is preserved.
* [ ] PDF pages are converted into individual page images.

## Question

* [ ] System detects question region.
* [ ] Multi-line questions are grouped into one question.
* [ ] Question text preserves original spelling and punctuation.
* [ ] Question crop is saved.

## Answer

* [ ] System detects answer region.
* [ ] One-paragraph answers remain one paragraph.
* [ ] Multi-paragraph answers are split before detailed OCR.
* [ ] Each paragraph receives a unique ID.
* [ ] Each paragraph crop is saved.

## OCR

* [ ] Line crops are generated before TrOCR.
* [ ] Every line crop is persisted.
* [ ] TrOCR processes line crops.
* [ ] OCR confidence is stored.
* [ ] OCR does not perform grammar correction.

## Markup

* [ ] Cancelled text is preserved.
* [ ] Cancelled text is wrapped in `<strikethrough>`.
* [ ] Caret insertions are preserved.
* [ ] Inserted text is wrapped in `<caret>`.
* [ ] Caret text is placed at its logical position.
* [ ] Highlights are preserved as spatial metadata.

## Formatting

* [ ] Physical line breaks are removed.
* [ ] Paragraph breaks are represented using `\n\n`.
* [ ] Original spelling is preserved.
* [ ] Original punctuation is preserved.
* [ ] Original capitalization is preserved.
* [ ] No translation occurs.

## Frontend

* [ ] Original image is displayed.
* [ ] Highlight overlays can be toggled.
* [ ] Paragraph bounding boxes can be displayed.
* [ ] Caret regions can be displayed.
* [ ] Strikethrough regions can be displayed.
* [ ] Clicking a region displays its crop.
* [ ] OCR result is displayed beside the crop.
* [ ] Low-confidence OCR is visibly flagged.
* [ ] Human reviewer can edit final text.

## LLM Review (optional, Section 39.1)

* [ ] LLM review is disabled by default and the pipeline behaves identically when disabled.
* [ ] LLM review runs only after markup reconstruction and before human review.
* [ ] Only ambiguous caret anchors and low-confidence regions are sent to the LLM.
* [ ] Caret anchor requests are multiple choice over rendered candidate positions.
* [ ] Invalid LLM anchor indices are rejected and the deterministic best guess is kept.
* [ ] Low-confidence review selects among TrOCR N-best candidates, not free transcription.
* [ ] Free-transcription fallback output is diff-validated and rejected if normalized.
* [ ] LLM suggestions are attached with `applied: false` until human confirmation.
* [ ] `LLMReview` records trigger, inputs, chosen result, and `agreedWithDeterministic`.
* [ ] The full page image is never sent to the LLM.
* [ ] Per-page call limit and caching are enforced.
* [ ] High-confidence OCR (>= 0.90) is never sent to the LLM.

---

# 43. Final Architecture Principle

The most important architectural decision is:

```text
                 IMAGE
                   │
        ┌──────────┴──────────┐
        │                     │
        ▼                     ▼
  SPATIAL ENGINE          OCR ENGINE
    OpenCV                  TrOCR
        │                     │
        │                     │
        ├── Question          ├── Text
        ├── Paragraph         └── Confidence
        ├── Line
        ├── Highlight
        ├── Strikethrough
        └── Caret
                 │
                 ▼
          RECONSTRUCTION
                 │
                 ▼
          HUMAN REVIEW
                 │
                 ▼
             FINAL JSON
```

**OpenCV determines *where*.
TrOCR determines *what was written*.
The reconstruction engine determines *how the spatial annotations are represented*.
The human reviewer determines *whether the final transcription is acceptable*.**

This separation is critical for achieving the required **character-level fidelity without sacrificing the visual evidence contained in the student's original script**.
