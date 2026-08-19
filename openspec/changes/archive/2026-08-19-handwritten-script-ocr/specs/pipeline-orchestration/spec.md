## Purpose

Wires the end-to-end pipeline stages into one orchestrator, tracks document progress through the processing state machine, retains all intermediate artifacts in a structured storage layout for debugging and model improvement, and defines the readable module structure of the POC.

## ADDED Requirements

### Requirement: Processing state machine
The system SHALL track each document through the states: UPLOADED → NORMALIZED → QUESTION_DETECTED → ANSWER_DETECTED → PARAGRAPHS_DETECTED → CROPS_GENERATED → OCR_PROCESSING → MARKUP_RECONSTRUCTION → REVIEW_REQUIRED → APPROVED → EXPORTED, with corrections from review looping back toward approval.

#### Scenario: State recorded per document
- **WHEN** a document completes a pipeline stage
- **THEN** its state advances to the corresponding state and the state is queryable

### Requirement: Artifact retention
The system MUST retain intermediate processing artifacts: original, rendered pages, deskewed image, binary image, highlight mask, line segmentation image, paragraph/line/word/caret/cancelled crops, per-crop OCR JSON, and final JSON.

#### Scenario: Debug artifacts available
- **WHEN** a document has been fully processed
- **THEN** all listed intermediate artifacts exist in the storage structure for inspection

### Requirement: Storage directory structure
The system SHALL organize storage into originals, rendered, processed (per-page intermediates), crops (per-page, by crop type), ocr (per-page JSON), and output (final document JSON).

#### Scenario: Structured storage layout
- **WHEN** any artifact is written
- **THEN** it is written to its designated directory within the storage structure

### Requirement: Single orchestrator with stage modules
The pipeline MUST be wired in one short orchestrator, with each stage a separate small module named after its responsibility (e.g. pdf_to_pages, detect_questions, detect_carets, crop_generator, run_trocr, reconstruct). Shared data structures MUST live in one models/schemas module. Magic numbers (thresholds, weights, epsilon) MUST be named constants or configuration values.

#### Scenario: Stage isolation
- **WHEN** a pipeline stage needs modification
- **THEN** the change is confined to that stage's module, with shared structures in the single schemas module and thresholds in named constants or config

### Requirement: Configurable parameters
Paragraph scoring weights, confidence thresholds, LLM review settings (enabled, model, triggers, gap epsilon, batch, per-page call limit, caching) MUST be configurable rather than hard-coded.

#### Scenario: Configuration changes behavior
- **WHEN** a configuration value such as a paragraph gap weight is changed
- **THEN** subsequent pipeline runs use the new value without code changes
