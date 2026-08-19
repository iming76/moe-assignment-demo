## MODIFIED Requirements

### Requirement: Crop inspector
When a user clicks a line, the frontend MUST show the original location, line
crop, Vision LLM result and confidence, validation state, and reconstructed text.

#### Scenario: Inspect a line
- **WHEN** a reviewer clicks a line overlay
- **THEN** the inspector shows its crop, literal text, confidence, uncertainty, and review status
