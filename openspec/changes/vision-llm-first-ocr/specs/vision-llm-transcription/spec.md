## Purpose

Provides literal, line-level Vision LLM transcription from immutable line
crops without allowing the model to normalize or invent student writing.

## ADDED Requirements

### Requirement: Vision LLM line transcription
The system SHALL transcribe each persisted line crop with a configured Vision
LLM and record literal text, confidence, model identifier, crop ID, request
schema version, and raw structured response.

#### Scenario: Line crop is transcribed
- **WHEN** a persisted line crop reaches transcription
- **THEN** the system records a traceable structured transcription result for that crop

### Requirement: Fidelity-constrained structured responses
The Vision LLM response MUST preserve visible spelling, grammar,
capitalization, punctuation, and language; it MUST identify uncertainty rather
than guessing and MUST NOT rewrite a paragraph or infer missing text. Visible
cancelled text MUST be preserved inside `<strikethrough>` tags and visible
caret-inserted text MUST be placed logically inside `<caret>` tags.

#### Scenario: Ambiguous handwriting is reported
- **WHEN** the model cannot read a span with sufficient confidence
- **THEN** the structured response identifies the uncertain span and the line is flagged for review

#### Scenario: Visible correction markup is preserved
- **WHEN** a line crop visibly contains cancelled text or caret-inserted text
- **THEN** the literal text preserves it using the required tag at its logical position

### Requirement: Bounded model use
Vision LLM requests MUST be subject to configurable per-page limits and
cache reuse. Lines that cannot be processed within those bounds
MUST be flagged for human review.

#### Scenario: Per-page limit reached
- **WHEN** a page reaches its configured Vision LLM call limit
- **THEN** remaining eligible items are not sent and are flagged for review
