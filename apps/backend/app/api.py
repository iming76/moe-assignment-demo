"""FastAPI endpoints (task 18).

Design decision 8 (no auth, POC):

- POST /documents            upload a document (multipart file) → runs the
                             pipeline to REVIEW_REQUIRED, returns documentId
- GET  /documents/{id}       document state + full JSON
- GET  /documents/{id}/artifacts/{path}  serve originals/rendered/crops/ocr

State transitions are validated by the state machine (review.py).
"""

from __future__ import annotations

import asyncio
import json
import shutil
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse

from .config import CONFIG
from .pipeline import process_document
from .schemas import Document
from .storage import StorageLayout

app = FastAPI(title="Handwritten Script OCR POC")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_documents: dict[str, Document] = {}

# Per-document progress broadcast: each connected SSE reader gets its own
# queue so /progress can be opened multiple times (e.g. tab refresh).
_progress_subscribers: dict[str, list[asyncio.Queue]] = {}
_TERMINAL_STATES = {"REVIEW_REQUIRED", "ERROR"}


def _publish_progress(document_id: str, payload: dict) -> None:
    for queue in _progress_subscribers.get(document_id, []):
        queue.put_nowait(payload)


def _layout(document_id: str) -> StorageLayout:
    return StorageLayout(document_id, root=CONFIG.storage.root)


def _next_document_id() -> str:
    """doc_NNN, skipping ids already present on disk (crops are immutable,
    so reusing an id from a prior server run collides on write)."""
    root = Path(CONFIG.storage.root)
    existing = {p.name for p in root.iterdir()} if root.exists() else set()
    n = len(_documents) + 1
    while f"doc_{n:03d}" in existing:
        n += 1
    return f"doc_{n:03d}"


@app.post("/documents")
async def upload_document(file: UploadFile) -> dict:
    suffix = Path(file.filename or "upload").suffix.lower()
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = Path(tmp.name)
    document_id = _next_document_id()
    loop = asyncio.get_running_loop()

    def on_state_change(state: str) -> None:
        loop.call_soon_threadsafe(
            _publish_progress, document_id, {"state": state}
        )

    def on_ocr_progress(completed: int, total: int) -> None:
        loop.call_soon_threadsafe(
            _publish_progress,
            document_id,
            {"state": "OCR_PROCESSING", "completed": completed, "total": total},
        )

    def run() -> None:
        try:
            document = process_document(
                tmp_path,
                document_id,
                on_state_change=on_state_change,
                on_ocr_progress=on_ocr_progress,
            )
            _documents[document_id] = document
        except Exception as exc:  # surfaced to the client via /progress
            loop.call_soon_threadsafe(
                _publish_progress,
                document_id,
                {"state": "ERROR", "detail": str(exc)},
            )
        finally:
            tmp_path.unlink(missing_ok=True)

    asyncio.get_running_loop().run_in_executor(None, run)
    return {"documentId": document_id, "state": "UPLOADED"}


@app.get("/documents/{document_id}/progress")
async def stream_progress(document_id: str) -> StreamingResponse:
    queue: asyncio.Queue = asyncio.Queue()
    _progress_subscribers.setdefault(document_id, []).append(queue)

    async def events():
        try:
            document = _documents.get(document_id)
            if document is not None:
                yield f"data: {json.dumps({'state': document.state})}\n\n"
                if document.state in _TERMINAL_STATES:
                    return
            while True:
                payload = await queue.get()
                yield f"data: {json.dumps(payload)}\n\n"
                if payload["state"] in _TERMINAL_STATES:
                    break
        finally:
            _progress_subscribers.get(document_id, []).remove(queue)

    return StreamingResponse(events(), media_type="text/event-stream")


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


