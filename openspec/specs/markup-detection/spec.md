# markup-detection Specification

## Purpose

Detects highlights, strikethroughs (cancelled text), and caret insertions as spatial metadata, independently from OCR, so the reconstruction engine can represent them without ever altering transcribed text.

## Requirements

### Requirement: Highlight detection
The system SHALL detect highlighted regions (e.g. yellow highlights) independently from OCR using color-space analysis (RGB to HSV, color mask, morphological cleanup, contour extraction) and record them as spatial metadata with bounding box and polygon.

#### Scenario: Yellow highlight detected
- **WHEN** a rendered page contains a yellow-highlighted passage
- **THEN** the system records a highlight object with id, type, bounding box, and polygon coordinates

#### Scenario: Highlight detection does not alter OCR
- **WHEN** a highlighted region overlaps transcribed text
- **THEN** the OCR text for that region is identical to what it would be without highlight detection

### Requirement: Strikethrough detection
The system SHALL identify strokes that cross handwriting (cancelled text) using signals such as long diagonal/horizontal strokes, intersection with handwriting, stroke orientation, stroke length, and overlap with text regions. Detected cancelled regions MUST be associated with the corresponding OCR text span and the cancelled text MUST remain in the output.

#### Scenario: Crossed-out text detected
- **WHEN** a handwriting region is crossed by a long diagonal stroke
- **THEN** the system records a cancelled region associated with the corresponding text span

### Requirement: Caret detection
The system SHALL detect caret insertions spatially: the caret symbol, the inserted text above or near the caret, and the anchor position in the original line.

#### Scenario: Caret with inserted text
- **WHEN** a page contains a caret symbol with inserted text written above it
- **THEN** the system records the caret bounding box, an insert crop for the inserted text, and the anchor line ID

### Requirement: Markup detection separation
Markup detection SHALL be a spatial responsibility only; it MUST NOT correct, modify, or influence OCR text content.

#### Scenario: Markup never changes transcription
- **WHEN** any highlight, strikethrough, or caret is detected
- **THEN** the literal OCR text produced for the affected crops is unchanged by the detection process
