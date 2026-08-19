# document-ingestion Specification

## Purpose

Accepts handwritten student scripts as images (PNG, JPG, JPEG, WEBP) or scanned/image-based/multi-page PDFs, preserves originals untouched, and normalizes every input into a common page-image representation that the rest of the pipeline consumes.

## Requirements

### Requirement: Image input support
The system SHALL accept PNG, JPG, JPEG, and WEBP image files as input documents.

#### Scenario: Single image upload
- **WHEN** a PNG, JPG, JPEG, or WEBP file is uploaded
- **THEN** the system normalizes it into a single PageImage with pageNumber, path, width, height, and dpi

### Requirement: PDF input support
The system SHALL accept scanned, image-based, and multi-page PDF files as input documents.

#### Scenario: Multi-page PDF upload
- **WHEN** a multi-page PDF is uploaded
- **THEN** each page is rendered into its own page image (page_001.png, page_002.png, ...) and each becomes a PageImage entry

### Requirement: Original preservation
The system MUST never modify the original uploaded file. Originals MUST be stored in a dedicated originals storage area, and rendered page images MUST be stored separately.

#### Scenario: Original file integrity
- **WHEN** any document (image or PDF) has been fully processed
- **THEN** the original uploaded file remains byte-for-byte unchanged and available in originals storage

### Requirement: Coordinate system consistency
All bounding boxes produced anywhere in the pipeline SHALL use the dimensions of the rendered page image as their coordinate system.

#### Scenario: Bounding box coordinates
- **WHEN** a spatial region (question, answer, paragraph, line, markup) is detected
- **THEN** its bounding box is expressed in rendered-page-image pixel coordinates

### Requirement: Unsupported input rejection
The system SHALL reject input files that are not PNG, JPG, JPEG, WEBP, or PDF with a clear error.

#### Scenario: Unsupported file type
- **WHEN** a file of an unsupported type (e.g. DOCX) is uploaded
- **THEN** the system rejects it with an error identifying the unsupported format and no pipeline state is created
