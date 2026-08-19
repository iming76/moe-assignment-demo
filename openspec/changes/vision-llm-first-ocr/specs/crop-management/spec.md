## MODIFIED Requirements

### Requirement: Crops generated and persisted before OCR
Question, answer, paragraph, line, and word crops MUST be saved before Vision
LLM transcription. The line crop is the only Vision LLM input.

#### Scenario: Crops exist before transcription
- **WHEN** the pipeline reaches Vision LLM transcription
- **THEN** every required line crop already exists in crop storage

### Requirement: Crop metadata
Every crop MUST have metadata recording id, type, pageNumber, path, bounding
box, createdAt, and parentId where applicable.

#### Scenario: Line metadata recorded
- **WHEN** a line crop is generated
- **THEN** its metadata identifies its parent, page coordinates, and immutable path
