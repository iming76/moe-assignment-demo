## MODIFIED Requirements

### Requirement: Line-level OCR
A configured OpenAI Vision LLM SHALL operate exclusively on persisted line-level crops,
producing literal transcription text per line crop.

#### Scenario: Line crop transcription
- **WHEN** a line crop is submitted for transcription
- **THEN** the system produces an OCR result recording cropId, literal text, confidence, model identifier, and response provenance

### Requirement: OpenAI-only OCR engine
The application MUST NOT load or invoke a local TrOCR model. OCR result
persistence MUST remain available as part of the OpenAI line-transcription path.

#### Scenario: Line OCR executes
- **WHEN** OCR processing handles a persisted line crop
- **THEN** it uses the configured OpenAI provider and persists the resulting OCR JSON without a local-model fallback

### Requirement: OCR responsibility limits
Vision LLM transcription MUST NOT correct spelling, grammar, punctuation,
capitalization, or language; it MUST NOT rewrite a paragraph, determine
paragraph boundaries, or invent markup. It MUST preserve visible cancelled text
inside `<strikethrough>` tags and visible caret-inserted text at its logical
position inside `<caret>` tags.

#### Scenario: OCR output is literal only
- **WHEN** the Vision LLM processes a line crop
- **THEN** its output contains literal transcription, required visible markup tags, and structured uncertainty only

### Requirement: Confidence and N-best candidates
OCR results MUST store a confidence score and uncertainty metadata. The system
MUST record a review-required outcome when the response is malformed or
declares uncertainty.

#### Scenario: Invalid response escalates
- **WHEN** a response is malformed or contains an invalid uncertainty range
- **THEN** the affected line is flagged for review
