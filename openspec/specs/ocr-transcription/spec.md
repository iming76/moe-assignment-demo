# ocr-transcription Specification

## Purpose

Runs TrOCR on line-level crops to produce literal transcription text with confidence scores and model provenance, under strict fidelity rules that forbid any correction, normalization, or translation of the student's writing.

## Requirements

### Requirement: Line-level OCR
TrOCR SHALL operate primarily on line-level crops, producing literal OCR text per line crop.

#### Scenario: Line crop transcription
- **WHEN** a line crop is passed to TrOCR
- **THEN** the system produces an OCR result recording cropId, literal text, confidence, and model identifier

### Requirement: OCR responsibility limits
TrOCR MUST NOT be responsible for paragraph detection, question detection, spelling correction, grammar correction, caret reconstruction, or strikethrough reconstruction.

#### Scenario: OCR output is literal only
- **WHEN** TrOCR processes any line crop
- **THEN** the output contains only the literal transcription with confidence; no structural or corrective transformation is applied

### Requirement: Spelling fidelity
The OCR and reconstruction pipeline MUST preserve the student's original spelling exactly, even when a word appears misspelled.

#### Scenario: Misspelling preserved
- **WHEN** the handwriting reads "teens" in any form TrOCR reads it
- **THEN** the transcribed text matches what was read verbatim with no spell correction applied

### Requirement: Grammar fidelity
The system MUST NOT correct grammar (e.g. MUST NOT change "more and more people start to use it" into "more and more people started using it").

#### Scenario: Grammar left untouched
- **WHEN** transcribed text contains non-standard grammar
- **THEN** the text passes through reconstruction unchanged

### Requirement: Punctuation fidelity
The system MUST NOT normalize punctuation (e.g. "However ," MUST NOT become "However,") unless the original handwriting clearly indicates the normalized form.

#### Scenario: Punctuation spacing preserved
- **WHEN** OCR produces text with non-standard punctuation spacing
- **THEN** the spacing is preserved in the final output

### Requirement: Language and capitalization fidelity
The system MUST NOT translate text and MUST preserve the student's original capitalization.

#### Scenario: No translation or recapitalization
- **WHEN** transcribed text is in any language or casing
- **THEN** the final output keeps the same language and the same capitalization as transcribed from the ink

### Requirement: Confidence and N-best candidates
OCR results MUST store a confidence score. TrOCR MUST support beam search producing N-best candidates for use by downstream ambiguity review.

#### Scenario: Confidence stored
- **WHEN** a line crop is transcribed
- **THEN** the OCR result includes a numeric confidence and model identifier, and N-best candidates are available when requested
