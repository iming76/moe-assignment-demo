## REMOVED Requirements

Separate geometry-based detectors and correction candidates remain removed.
Visible markup is represented directly in the Vision LLM line transcription.

### Requirement: Strikethrough detection
The system SHALL identify strokes that cross handwriting (cancelled text) using
signals such as long diagonal/horizontal strokes, intersection with handwriting,
stroke orientation, stroke length, and overlap with text regions. Detected
cancelled regions MUST be associated with the corresponding OCR text span and
the cancelled text MUST remain in the output.

#### Scenario: Crossed-out text detected
- **WHEN** a handwriting region is crossed by a long diagonal stroke
- **THEN** the system records a cancelled region associated with the corresponding text span

### Requirement: Caret detection
The system SHALL detect caret insertions spatially: the caret symbol, the
inserted text above or near the caret, and the anchor position in the original line.

#### Scenario: Caret with inserted text
- **WHEN** a page contains a caret-like symbol with inserted text above it
- **THEN** the system records the caret bounding box, an insert crop for the inserted text, and the anchor line ID
