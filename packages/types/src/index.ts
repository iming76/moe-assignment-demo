/**
 * @moe-research/types
 *
 * Single shared contract between the Python backend and the Next.js
 * frontend. Mirrors backend/schemas.py 1:1 — any JSON shape change must
 * land here first. camelCase keys throughout (spec Sections 5.1, 9, 14,
 * 17, 19, 22, 24, 31, 39.1.4).
 */

// ---------------------------------------------------------------------------
// Geometry / normalization
// ---------------------------------------------------------------------------

export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface Point {
  x: number;
  y: number;
}

/** Normalized page representation (spec Section 5.1). */
export interface PageImage {
  pageNumber: number;
  path: string;
  width: number;
  height: number;
  dpi: number;
}

// ---------------------------------------------------------------------------
// Spatial detections
// ---------------------------------------------------------------------------

/** Spec Section 9. */
export interface Question {
  id: string;
  bbox: BoundingBox;
  cropPath: string;
  lines: string[];
  text: string;
  confidence?: number;
}

export interface OCRToken {
  text: string;
  confidence: number;
}

/** One physical handwriting line inside a paragraph (spec Section 14). */
export interface OCRLine {
  id: string;
  bbox: BoundingBox;
  cropId: string;
  text: string;
  confidence?: number;
}

// ---------------------------------------------------------------------------
// Markup
// ---------------------------------------------------------------------------

/** Spec Section 17. */
export interface Highlight {
  id: string;
  type: "highlight";
  bbox?: BoundingBox;
  polygon: Point[];
}

/** Spec Section 18 — cancelled text region. */
export interface Strikethrough {
  id: string;
  type: "strikethrough";
  bbox?: BoundingBox;
  cropPath?: string;
  strokeBbox?: BoundingBox;
  lineId?: string;
}

/** Spec Section 39.1.4 — applied stays false until a human confirms. */
export interface LLMReview {
  id: string;
  targetId: string;
  trigger: "caret_anchor_ambiguity" | "low_confidence";
  inputs: {
    cropPaths: string[];
    candidates: string[];
  };
  rawResponse: object | null;
  /** Candidate / anchor index chosen. */
  chosen: string | number | null;
  agreedWithDeterministic: boolean;
  applied: boolean;
  model: string;
  latencyMs: number;
}

/** Spec Section 19 — caret insertion markup. */
export interface Caret {
  id: string;
  type: "caret";
  caret: {
    bbox: BoundingBox;
  };
  insertCrop: string;
  anchorLineId: string;
  /** Inserted-text region above the caret symbol (internal use). */
  insertBbox?: BoundingBox;
  /** Candidate gap indices for ambiguous anchors (rendered as tick marks). */
  anchorCandidates?: number[];
  llmReview?: LLMReview;
}

export type Markup = Strikethrough | Caret;

// ---------------------------------------------------------------------------
// Crops & OCR
// ---------------------------------------------------------------------------

export type CropType =
  | "question"
  | "answer"
  | "paragraph"
  | "line"
  | "word"
  | "cancelled"
  | "caret";

/** Spec Section 22 — immutable once written. */
export interface Crop {
  id: string;
  type: CropType;
  pageNumber: number;
  parentId?: string;
  path: string;
  bbox: BoundingBox;
  createdAt: string;
}

export interface OCRCandidate {
  text: string;
  confidence: number;
}

/** Spec Section 24 — literal text only, never corrected. */
export interface OCRResult {
  cropId: string;
  text: string;
  confidence: number;
  model: string;
  tokens?: OCRToken[];
  /** TrOCR beam-search N-best candidates. */
  candidates?: OCRCandidate[];
  processingTimeMs?: number;
  llmReview?: LLMReview;
}

// ---------------------------------------------------------------------------
// Document assembly
// ---------------------------------------------------------------------------

/** Spec Section 14. */
export interface Paragraph {
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

/** Answer region: bbox + paragraphs (spec Sections 10, 31). */
export interface Answer {
  bbox: BoundingBox;
  cropPath?: string;
  paragraphs: Paragraph[];
}

export interface DocumentPage {
  pageNumber: number;
  image: PageImage;
  question?: Question;
  answer?: Answer;
  highlights: Highlight[];
  carets: Caret[];
  crops: Crop[];
  ocr: OCRResult[];
}

export interface DocumentSource {
  type: "image" | "pdf";
  originalPath: string;
}

/** Spec Section 30 — question + answer with \n\n between paragraphs. */
export interface FinalOutput {
  question: string;
  answer: string;
}

/** Human review correction (spec Section 34). */
export interface ReviewCorrection {
  id: string;
  cropId: string;
  originalText: string;
  correctedText: string;
  reason?: string;
  createdAt?: string;
}

/** Processing state machine (spec Section 40). */
export type DocumentState =
  | "UPLOADED"
  | "NORMALIZED"
  | "QUESTION_DETECTED"
  | "ANSWER_DETECTED"
  | "PARAGRAPHS_DETECTED"
  | "CROPS_GENERATED"
  | "OCR_PROCESSING"
  | "MARKUP_RECONSTRUCTION"
  | "REVIEW_REQUIRED"
  | "APPROVED"
  | "EXPORTED";

/** Complete internal JSON (spec Section 31). */
export interface Document {
  documentId: string;
  source: DocumentSource;
  state: DocumentState;
  pages: DocumentPage[];
  final: FinalOutput;
  corrections: ReviewCorrection[];
  llmReviews: LLMReview[];
}
