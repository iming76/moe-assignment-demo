## Purpose

Combines literal OCR text with spatial and markup metadata to produce the final transcription: strikethrough and caret markup placed at their correct logical positions, physical line breaks joined within paragraphs, paragraphs separated by blank lines, and the complete internal JSON document assembled.

## ADDED Requirements

### Requirement: Reconstruction inputs
The reconstruction engine SHALL combine OCR text, spatial metadata, and markup metadata to produce final text. It MUST NOT re-transcribe or re-interpret image content.

#### Scenario: Reconstruction from metadata
- **WHEN** OCR results and markup metadata exist for a paragraph
- **THEN** the reconstruction engine produces the final paragraph text using only those recorded inputs

### Requirement: Caret reconstruction
Caret-inserted text MUST be inserted at its logical position within the line, wrapped in caret markup. The system MUST NOT simply append inserted text to the end of the paragraph.

#### Scenario: Caret inserted mid-sentence
- **WHEN** OCR reads "send a text message to their classmate" and a caret with inserted text "in seconds" is anchored between "text" and "message"
- **THEN** the reconstructed text is "send a text <caret>in seconds</caret> message to their classmate"

### Requirement: Strikethrough reconstruction
Cancelled text MUST remain visible in the transcription, wrapped in strikethrough markup.

#### Scenario: Cancelled word preserved
- **WHEN** OCR reads "The candidate felt nervous excited." and "nervous" is marked as cancelled
- **THEN** the reconstructed text is "The candidate felt <strikethrough>nervous</strikethrough> excited."

### Requirement: Paragraph formatting
Physical handwriting line breaks MUST NOT appear in final text; lines within a paragraph are joined with single spaces. Separate paragraphs MUST be separated by a blank line (two newlines).

#### Scenario: Line joining
- **WHEN** a paragraph consists of three physical OCR lines
- **THEN** the final paragraph text joins them with single spaces and contains no internal line breaks

#### Scenario: Paragraph separation
- **WHEN** an answer contains three paragraphs
- **THEN** the final answer text separates them with blank lines

### Requirement: Final output shape
The final output SHALL contain the question text and the answer text (paragraphs joined with blank-line separation). The complete internal JSON MUST additionally record documentId, source (type and original path), per-page image info, question and answer objects with crops and bounding boxes, paragraphs with lines, highlights, and markups, and the final section.

#### Scenario: Complete internal JSON
- **WHEN** reconstruction completes for a document
- **THEN** the output JSON contains documentId, source, pages with image/question/answer/paragraph details, and the final question/answer section, and every text fragment is traceable to a crop

### Requirement: Highlights preserved as metadata
Highlights MUST be preserved as spatial metadata attached to paragraphs in the output; they MUST NOT alter the transcription text.

#### Scenario: Highlight recorded without text change
- **WHEN** a paragraph contains a highlighted region
- **THEN** the paragraph output includes the highlight metadata and the text is unchanged by the highlight
