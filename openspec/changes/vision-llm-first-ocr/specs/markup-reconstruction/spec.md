## REMOVED Requirements

The removed requirements below describe separate detected markup objects.
Reconstruction instead preserves tags already emitted in literal line OCR.

### Requirement: Caret reconstruction
Caret-inserted text MUST be inserted at its logical position within the line,
wrapped in caret markup. The system MUST NOT simply append inserted text to the
end of the paragraph.

#### Scenario: Caret inserted mid-sentence
- **WHEN** OCR reads "send a text message to their classmate" and a caret with inserted text "in seconds" is anchored between "text" and "message"
- **THEN** the reconstructed text is "send a text <caret>in seconds</caret> message to their classmate"

### Requirement: Strikethrough reconstruction
Cancelled text MUST remain visible in the transcription, wrapped in
strikethrough markup.

#### Scenario: Cancelled word preserved
- **WHEN** OCR reads "The candidate felt nervous excited." and "nervous" is marked as cancelled
- **THEN** the reconstructed text is "The candidate felt <strikethrough>nervous</strikethrough> excited."

## ADDED Requirements

### Requirement: Tagged line and paragraph reconstruction
Reconstruction MUST preserve `<strikethrough>` and `<caret>` tags emitted by
line OCR, join physical lines within a paragraph using spaces, and join original
paragraphs using `\n\n`.

#### Scenario: Physical lines and paragraphs reconstructed
- **WHEN** tagged line OCR results are assembled from multiple original paragraphs
- **THEN** physical line breaks are removed, tags remain unchanged, and paragraph boundaries are represented by `\n\n`
