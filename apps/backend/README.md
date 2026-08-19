# backend

Python pipeline for the handwritten student script OCR POC.

Stage-per-module layout (design.md decision 3), packaged under `app/` and
grouped into subpackages by pipeline phase. `app/pipeline.py` is the short
orchestrator; shared structures live in `app/schemas.py` (mirrored by
`packages/types`); thresholds/weights live in `app/config.py` +
`app/config.yaml`.

    app/
      api.py                FastAPI endpoints (`uv run uvicorn app.api:app`)
      pipeline.py            orchestrator + state machine advancement
      review.py              manual correction workflow
      state_machine.py       document state transitions
      config.py / config.yaml  thresholds/weights
      schemas.py              shared data structures
      storage.py              artifact storage layout
      ingest/
        pages.py              PDF → per-page rendered images
      imaging/
        normalize_image.py    image preprocessing (grayscale → morphology)
        opencv_analysis.py    line/word segmentation shared OpenCV helpers
        crop_generator.py     persist all crops + metadata before OCR
      detect/
        questions.py          question detection + line grouping
        answers.py             answer region detection
        paragraphs.py          paragraph boundary detection/splitting
        highlights.py          highlight detection
        strikethroughs.py      strikethrough detection
        carets.py               caret detection
      ocr/
        trocr.py               TrOCR over line crops (literal text only)
        reconstruct.py         OCR + spatial + markup → final JSON
        llm_review.py          optional gated LLM ambiguity review

`storage/` (runtime document data) stays at the package root, alongside
`pyproject.toml`/`uv.lock`, since it's generated output rather than source.

This directory lives outside the turbo workspace by design.
