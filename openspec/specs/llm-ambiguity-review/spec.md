# llm-ambiguity-review Specification

## Purpose

Provides an optional, disabled-by-default, final-stage LLM review pass limited to ambiguous caret anchors and low-confidence OCR regions, using multiple-choice selection over ink-derived candidates so the LLM can never structurally autocorrect, with all suggestions left non-authoritative until a human confirms.

## Requirements

### Requirement: Optional and final stage
The LLM review stage MUST be disabled by default; when disabled the pipeline behavior MUST be identical to when the stage does not exist. When enabled, it MUST run after markup reconstruction and immediately before human review.

#### Scenario: Disabled by default
- **WHEN** the pipeline runs with default configuration
- **THEN** no LLM call is made and pipeline output is identical to a pipeline without the LLM stage

#### Scenario: Position when enabled
- **WHEN** the LLM stage is enabled
- **THEN** it runs after markup reconstruction and before human review, only on collected ambiguity flags

### Requirement: Trigger A — ambiguous caret anchor
The deterministic rule (caret tip x projected onto the anchor line, snapped to the nearest inter-word gap) MUST run first. The LLM SHALL be escalated to only when the deterministic step is ambiguous: two candidate gaps within gap_epsilon_px, caret x inside a word bbox, clustered carets or orphaned carets/inserted text, low anchor-line OCR confidence, or unclear line assignment.

#### Scenario: Unambiguous caret never sent to LLM
- **WHEN** a caret projection lands clearly on a single inter-word gap
- **THEN** the deterministic anchor is used and no LLM request is made

#### Scenario: Ambiguous caret escalated
- **WHEN** two candidate gaps fall within gap_epsilon_px of the caret projection
- **THEN** the caret is flagged for LLM review

### Requirement: Multiple-choice caret requests
Caret anchor LLM requests MUST be multiple choice, never open-ended: an anchor-line crop with numbered tick marks at each candidate gap, the caret crop, and the inserted-text crop, asking which numbered position is the insertion point, with strict JSON output of anchorIndex, confidence, and reason.

#### Scenario: Anchor request shape
- **WHEN** an ambiguous caret is sent for LLM review
- **THEN** the request contains only the anchor-line crop with numbered candidate tick marks, the caret crop, and the inserted-text crop, and requires a strict JSON response

#### Scenario: Invalid anchor index rejected
- **WHEN** the LLM returns an anchorIndex that is not one of the rendered candidate indices
- **THEN** the response is rejected, the deterministic best guess is kept, and the item is flagged for human review

### Requirement: Trigger B — low-confidence regions
Regions with confidence below 0.70 SHALL be sent to LLM review when enabled; regions at 0.70–0.89 only when include_review_recommended is true; regions at or above 0.90 MUST never be sent.

#### Scenario: High confidence never reviewed
- **WHEN** an OCR result has confidence >= 0.90
- **THEN** it is never sent to the LLM regardless of configuration

### Requirement: Candidate selection, not free transcription
Low-confidence review MUST select among TrOCR N-best candidates produced with beam search; the LLM chooses a candidate index. Free-form transcription is permitted only as a documented fallback, and its output MUST be validated by character diff against the TrOCR top-1 candidate and rejected if the diff suggests normalization.

#### Scenario: Selection among N-best candidates
- **WHEN** a low-confidence line crop is sent for review
- **THEN** the request includes the crop, at most one context line above and below, and the N-best candidates with confidences, and the LLM responds with a candidate index

#### Scenario: Normalized free transcription rejected
- **WHEN** a free-form fallback response differs from the top-1 candidate in ways suggesting punctuation, capitalization, or word-form normalization
- **THEN** the response is rejected

### Requirement: Non-authoritative suggestions
LLM outputs MUST be attached to existing objects as suggestions with applied=false until a human reviewer confirms. The LLM MUST never overwrite OCR text, spatial metadata, or markup.

#### Scenario: Suggestion awaits confirmation
- **WHEN** the LLM returns a valid choice
- **THEN** an LLMReview record is attached with applied=false and nothing in the transcription changes until human confirmation

### Requirement: Request scope limits
Per call the LLM MUST receive only the target crop, at most one context line above and below when anchoring depends on it, spatial metadata, OCR candidates with confidences, and the fidelity contract. The full page image MUST never be sent.

#### Scenario: Full page never sent
- **WHEN** any LLM review request is constructed
- **THEN** the payload contains no full page image

### Requirement: Review recording and limits
Each LLMReview MUST record id, targetId, trigger, inputs, rawResponse, chosen result, agreedWithDeterministic, applied, model, and latencyMs. Per-page call limits and response caching (keyed by crop bytes plus candidate list) MUST be enforced when enabled.

#### Scenario: Disagreement tracked
- **WHEN** the LLM choice differs from the deterministic result
- **THEN** agreedWithDeterministic is recorded as false on the LLMReview record
