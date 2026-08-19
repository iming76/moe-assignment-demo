## Purpose

Performs all OpenCV-driven spatial analysis on rendered page images: image preprocessing, question detection with multi-line grouping, answer-region detection, and logical paragraph detection and splitting that happens before detailed OCR — establishing where everything is on the page without ever touching text content.

## ADDED Requirements

### Requirement: Image preprocessing pipeline
The system SHALL preprocess rendered page images through grayscale conversion, denoising, contrast normalization, deskewing, thresholding, and morphological processing to prepare for line and region detection. Processed images MUST be retained as intermediate artifacts only, never replacing the original or rendered image.

#### Scenario: Preprocessing a rendered page
- **WHEN** a rendered page image enters preprocessing
- **THEN** grayscale, deskewed, and binary intermediate images are produced and stored, and the original rendered image remains available

### Requirement: Question detection
The system SHALL detect the question region before processing the answer, using indicators such as Q1/Q2/QN 1/Question prefixes, question marks, question-like sentence structure, position near the top of the answer area, larger gap after the question, and handwriting following the question.

#### Scenario: Detect a prefixed question
- **WHEN** a page contains text beginning with "QN 1:" followed by a sentence
- **THEN** the system detects it as a question region with a bounding box, and the question is recorded before any answer processing begins

### Requirement: Question line grouping
Physical lines belonging to the same question MUST be merged into a single question. Physical line breaks MUST NOT appear in the final question text.

#### Scenario: Multi-line question grouping
- **WHEN** the question "QN 1: What are the advantages and disadvantages of teens using" continues on the next physical line with "social media in communicating with others?"
- **THEN** both lines are grouped into one question with text "QN 1: What are the advantages and disadvantages of teens using social media in communicating with others?" and no internal line break

### Requirement: Answer region detection
The system SHALL detect the answer region after the question, using vertical position, blank-line spacing, handwriting density, the question bounding box, line grouping, and indentation. The answer region MUST be stored as a bounding box starting after the question region and its associated spacing.

#### Scenario: Answer region below question
- **WHEN** a question region has been detected and handwriting content follows after the question spacing
- **THEN** the system records an answer bounding box covering the handwritten content below the question

### Requirement: Logical paragraph detection before OCR
The system SHALL distinguish physical lines from logical paragraphs and perform paragraph detection and splitting before detailed OCR runs.

#### Scenario: Multiple physical lines form one paragraph
- **WHEN** an answer contains five consecutive physical handwriting lines with uniform spacing
- **THEN** the system treats them as one logical paragraph with a single paragraph crop

#### Scenario: Multiple paragraphs split before OCR
- **WHEN** an answer contains distinct paragraphs separated by significant vertical gaps, indentation, or blank lines
- **THEN** each paragraph is split into its own region with its own bounding box and crop before any OCR runs, and each paragraph receives a unique ID and order number

### Requirement: Paragraph boundary scoring
Paragraph boundaries SHALL be detected using vertical gap between handwriting lines as the primary signal, with indentation, blank lines, handwriting density, horizontal starting position, line spacing, and paragraph length as secondary signals combined via a configurable weighted score.

#### Scenario: Large vertical gap signals boundary
- **WHEN** the vertical gap between two consecutive handwriting lines exceeds the configured threshold relative to normal line spacing
- **THEN** the system marks a paragraph boundary between them

### Requirement: Header exclusion
The system SHALL exclude page headers (e.g. student name, exam metadata) from the answer region.

#### Scenario: Header not treated as answer
- **WHEN** a page has header content above the question
- **THEN** the header is excluded from the answer region and does not appear in the answer text
