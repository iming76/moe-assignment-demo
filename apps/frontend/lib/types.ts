/**
 * Shared contract mirroring the Python backend's schemas.py 1:1 — any JSON
 * shape change must land here first. camelCase keys throughout (spec
 * Sections 5.1, 9, 14, 17, 22, 24, and 31).
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
// Highlight markup
// ---------------------------------------------------------------------------

/** Spec Section 17. */
export interface Highlight {
  id: string;
  type: "highlight";
  bbox?: BoundingBox;
  polygon: Point[];
}

/** Optional audit record for low-confidence OCR review. */
export interface LLMReview {
  id: string;
  targetId: string;
  trigger: "low_confidence";
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

// ---------------------------------------------------------------------------
// Crops & OCR
// ---------------------------------------------------------------------------

export type CropType =
  | "question"
  | "answer"
  | "paragraph"
  | "line"
  | "word";

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

export interface UncertaintyRange { start: number; end: number; reason?: string; }

/** Spec Section 24 — literal text only, never corrected. */
export interface OCRResult {
  cropId: string;
  text: string;
  confidence: number;
  model: string;
  tokens?: OCRToken[];
  processingTimeMs?: number;
  llmReview?: LLMReview;
  requestSchemaVersion?: string;
  cacheKey?: string;
  rawResponse?: Record<string, unknown>;
  uncertainty?: UncertaintyRange[];
  validationState: "valid" | "invalid" | "unavailable";
  reviewState: "pending" | "required" | "accepted" | "rejected" | "corrected";
  reviewRequiredReason?: string;
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

export interface ReviewDecision {
  id: string; targetId: string; targetType: "ocr";
  decision: "accept" | "reject" | "correct"; value?: unknown; reason?: string; createdAt?: string;
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
  reviewDecisions: ReviewDecision[];
}
