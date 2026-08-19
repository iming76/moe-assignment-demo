## MODIFIED Requirements

### Requirement: Processing state machine
The system SHALL track each document through the states: UPLOADED → NORMALIZED
→ QUESTION_DETECTED → ANSWER_DETECTED → PARAGRAPHS_DETECTED → CROPS_GENERATED
→ OCR_PROCESSING → MARKUP_RECONSTRUCTION → REVIEW_REQUIRED → APPROVED →
EXPORTED, with corrections from review looping back toward approval.

#### Scenario: Vision transcription recorded
- **WHEN** line transcription completes for a document
- **THEN** the document advances through OCR_PROCESSING before reconstruction

### Requirement: Configurable parameters
Paragraph scoring weights, confidence thresholds, and Vision LLM settings
(provider, model, request schema version, per-page call limit, and caching)
MUST be configurable rather than hard-coded.

#### Scenario: Vision configuration changes behavior
- **WHEN** an operator changes a Vision LLM call limit or model setting
- **THEN** subsequent pipeline runs use the new setting without code changes
