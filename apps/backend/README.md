# backend

Python pipeline for the handwritten student script OCR POC.

Stage-per-module layout (design.md decision 3), packaged under `app/` and
grouped into subpackages by pipeline phase. `app/pipeline.py` is the short
orchestrator; shared structures live in `app/schemas.py`; thresholds/weights
live in `app/config.py` + `app/config.yaml`.

    app/
      api.py                FastAPI endpoints (`uv run uvicorn app.api:app`)
      pipeline.py            orchestrator + state machine advancement
      review.py              review-required flagging + confidence classification
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
      ocr/
        vision_llm.py          OpenAI Vision over line crops
        prompts/               Vision LLM prompt text (e.g. line_transcription.md)
        reconstruct.py         line OCR → final JSON

`storage/` (runtime document data, gitignored) stays at the package root,
alongside `pyproject.toml`/`uv.lock`, since it's generated output rather than
source.

Run with `uv sync` then `uv run uvicorn app.api:app --reload`, or via the
root workspace: `pnpm --filter @moe-assignment-demo/backend dev`. Tests:
`uv run python -m unittest discover -s tests -v`.
