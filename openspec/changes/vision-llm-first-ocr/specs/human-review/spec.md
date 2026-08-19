## ADDED Requirements

### Requirement: Vision LLM provenance review
The review flow MUST expose the source line crop, structured Vision LLM result,
confidence, uncertainty, and validation state for each flagged transcription.

#### Scenario: Reviewer inspects uncertain transcription
- **WHEN** a reviewer opens an uncertain Vision LLM line result
- **THEN** they can compare its text and provenance against the immutable source crop before correcting or accepting it
