## Purpose

Generates, persists, and catalogs all image crops (question, answer, paragraph, line, word, cancelled, caret) with bounding-box metadata before any OCR runs, keeping crops immutable so OCR models can be swapped or re-run without repeating segmentation.

## ADDED Requirements

### Requirement: Crops generated and persisted before OCR
All crops of types question, answer, paragraph, line, word, cancelled, and caret MUST be saved before TrOCR runs. Every crop MUST be persisted to storage organized by crop type.

#### Scenario: Crops exist before transcription
- **WHEN** the pipeline reaches the OCR stage
- **THEN** every question, answer, paragraph, line, word, cancelled, and caret crop for the document already exists in crop storage

### Requirement: Crop immutability
Once a crop has been generated, it MUST NOT be modified.

#### Scenario: Re-running OCR on existing crops
- **WHEN** a different OCR model is run on a previously processed document
- **THEN** the existing crops are reused unchanged without re-segmentation

### Requirement: Crop metadata
Every crop MUST have metadata recording id, type, pageNumber, path, bounding box, createdAt, and parentId where applicable.

#### Scenario: Crop metadata recorded
- **WHEN** a line crop is generated
- **THEN** its metadata records the line type, parent paragraph id, page number, file path, and bounding box in rendered-page coordinates

### Requirement: Crop traceability
Every extracted text fragment MUST be traceable back to an image crop through its cropId.

#### Scenario: Text fragment traced to crop
- **WHEN** any OCR result is inspected
- **THEN** its cropId identifies the exact crop file and bounding box from which the text was transcribed
