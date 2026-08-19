# backend

Python pipeline for the handwritten student script OCR POC.

Stage-per-module layout (design.md decision 3). `pipeline.py` is the short
orchestrator; shared structures live in `schemas.py` (mirrored by
`packages/types`); thresholds/weights live in `config.py` + `config.yaml`.

Stage modules:

    pdf_to_pages.py        PDF → per-page rendered images
    normalize_image.py     image preprocessing (grayscale → morphology)
    detect_questions.py    question detection + line grouping
    detect_answers.py      answer region detection
    detect_paragraphs.py   paragraph boundary detection/splitting
    opencv_analysis.py     line/word segmentation shared OpenCV helpers
    detect_highlights.py   highlight detection
    detect_strikethroughs.py  strikethrough detection
    detect_carets.py       caret detection
    crop_generator.py      persist all crops + metadata before OCR
    run_trocr.py           TrOCR over line crops (literal text only)
    reconstruct.py         OCR + spatial + markup → final JSON
    llm_review.py          optional gated LLM ambiguity review
    pipeline.py            orchestrator + state machine advancement

This directory lives outside the turbo workspace by design.
