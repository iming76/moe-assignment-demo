## Purpose

A Next.js/TypeScript review interface that shows the original image as the primary visual source, with zoom/pan viewing, toggleable spatial overlays, a crop inspector linking every object to its crop and OCR result, paragraph navigation, confidence visualization, and manual correction of the final text.

## ADDED Requirements

### Requirement: Original image viewer
The frontend MUST display the original rendered page image with zoom, pan, page navigation, and original resolution support.

#### Scenario: Navigate and zoom pages
- **WHEN** a reviewer opens a multi-page document
- **THEN** they can navigate between pages and zoom/pan each page at original resolution

### Requirement: Toggleable overlays
The frontend MUST provide toggles for overlays of questions, answers, paragraphs, lines, highlights, strikethroughs, and carets drawn over the original image in the original image coordinate system.

#### Scenario: Toggle paragraph overlay
- **WHEN** a reviewer enables the paragraph overlay
- **THEN** paragraph bounding boxes are drawn on the page image aligned to their recorded coordinates

### Requirement: Crop inspector
When a user clicks an object, the frontend MUST show the original location, the corresponding crop, the TrOCR result, and the final reconstructed text.

#### Scenario: Inspect a clicked line
- **WHEN** a reviewer clicks a line overlay
- **THEN** the inspector shows the line crop, its OCR text and confidence, and the reconstructed text containing it

### Requirement: Paragraph navigation
The user MUST be able to select Question → Answer → Paragraph N. Selecting a paragraph MUST highlight its bounding box on the original page, display the paragraph crop, its line crops, detected highlights, cancelled text, caret insertions, OCR confidence, and allow manual correction.

#### Scenario: Select a paragraph
- **WHEN** a reviewer selects Paragraph 2 of an answer
- **THEN** its bounding box is highlighted on the page and the panel shows the paragraph crop, line crops, highlights, cancelled text, caret insertions, confidence, and an editable text field

### Requirement: Confidence visualization
Low-confidence OCR regions MUST be visibly flagged in the UI according to the configured thresholds.

#### Scenario: Low-confidence line flagged
- **WHEN** the document contains a line with confidence below 0.70
- **THEN** that line is visibly flagged in the viewer and review flow

### Requirement: Manual correction UI
The reviewer MUST be able to edit the final reconstructed text from the frontend.

#### Scenario: Edit final text
- **WHEN** a reviewer modifies text in the correction editor
- **THEN** the change is saved to the document's review state

### Requirement: Shared type contract
The frontend MUST consume shared TypeScript types that mirror the backend JSON schemas.

#### Scenario: Type parity
- **WHEN** the backend JSON schema changes
- **THEN** the shared types package is the single contract both sides update against
