"""FastAPI endpoints (task 18).

Design decision 8 (no auth, POC):

- POST /documents            upload a document (multipart file) → runs the
                             pipeline to REVIEW_REQUIRED, returns documentId
- GET  /documents/{id}       document state + full JSON
- GET  /documents/{id}/artifacts/{path}  serve originals/rendered/crops/ocr
- POST /documents/{id}/corrections       submit a manual correction
- POST /documents/{id}/approve           approve + export final JSON

State transitions are validated by the state machine (review.py).
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse

from config import CONFIG
from pipeline import finalize_document, process_document
from review import submit_correction
from schemas import Document
from storage import StorageLayout

app = FastAPI(title="Handwritten Script OCR POC")

_documents: dict[str, Document] = {}


def _layout(document_id: str) -> StorageLayout:
    return StorageLayout(document_id, root=CONFIG.storage.root)


@app.post("/documents")
async def upload_document(file: UploadFile) -> dict:
    suffix = Path(file.filename or "upload").suffix.lower()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)
    document_id = f"doc_{len(_documents) + 1:03d}"
    try:
        document = process_document(tmp_path, document_id)
    except ValueError as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    finally:
        tmp_path.unlink(missing_ok=True)
    _documents[document_id] = document
    return {"documentId": document_id, "state": document.state}


@app.get("/documents/{document_id}")
async def get_document(document_id: str) -> dict:
    document = _documents.get(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Unknown document")
    return document.to_json()


@app.get("/documents/{document_id}/artifacts/{path:path}")
async def get_artifact(document_id: str, path: str) -> FileResponse:
    layout = _layout(document_id)
    target = (layout.doc_root / path).resolve()
    if not str(target).startswith(str(layout.doc_root.resolve())):
        raise HTTPException(status_code=400, detail="Path escapes storage")
    if not target.exists():
        raise HTTPException(status_code=404, detail="Artifact not found")
    return FileResponse(target)


@app.post("/documents/{document_id}/corrections")
async def post_correction(document_id: str, payload: dict) -> dict:
    document = _documents.get(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Unknown document")
    try:
        correction = submit_correction(
            document,
            payload["cropId"],
            payload["correctedText"],
            payload.get("reason", ""),
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return correction.to_json()


@app.post("/documents/{document_id}/approve")
async def approve_document(document_id: str) -> dict:
    document = _documents.get(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Unknown document")
    layout = _layout(document_id)
    rel = finalize_document(document, layout)
    return {"state": document.state, "output": rel}
