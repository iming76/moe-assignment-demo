## Purpose

Provides the review state flow after OCR and reconstruction: configurable confidence thresholds flag low-confidence regions, a reviewer inspects and corrects the transcription against the visual evidence, approves the document, and the approved result can be exported.

## ADDED Requirements

### Requirement: Review state flow
The system SHALL move a processed document from OCR completion into a Review Required state, through Human Review, to Approve. Low-confidence regions MUST be automatically flagged for review.

#### Scenario: Document enters review
- **WHEN** markup reconstruction (and optional LLM review) completes
- **THEN** the document enters the Review Required state with flagged regions listed

### Requirement: Configurable confidence thresholds
Confidence thresholds SHALL be configurable with defaults: confidence >= 0.90 accepted, 0.70–0.89 review recommended, below 0.70 review required.

#### Scenario: Low confidence flagged
- **WHEN** a line OCR result has confidence 0.54
- **THEN** it is recorded with reviewRequired=true and surfaced in the review flow

#### Scenario: Thresholds configurable
- **WHEN** an operator changes the configured thresholds
- **THEN** flagging behavior follows the new thresholds on subsequent processing

### Requirement: Manual correction
A human reviewer MUST be able to correct the final text during review. Corrections MUST be recorded against the document.

#### Scenario: Reviewer edits text
- **WHEN** a reviewer corrects a paragraph's transcription
- **THEN** the corrected text replaces the OCR-derived text in the document's review state and the correction is recorded

### Requirement: Approval and export
The system SHALL allow a reviewer to approve a reviewed document and export the approved final output.

#### Scenario: Approve then export
- **WHEN** a reviewer approves a document
- **THEN** the document reaches the APPROVED state and its final JSON can be exported

### Requirement: LLM suggestion confirmation
When LLM review suggestions exist, they MUST only take effect after a human reviewer confirms them, at which point applied becomes true.

#### Scenario: Confirming an LLM suggestion
- **WHEN** a reviewer confirms an LLM caret-anchor suggestion
- **THEN** the suggestion is applied and recorded with applied=true; unconfirmed suggestions remain applied=false
