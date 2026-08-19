"""Document normalization: ingest images/PDFs into PageImage[] (tasks 5a/5b).

Spec Section 5.1 + document-ingestion capability:

- PNG/JPG/JPEG/WEBP → single PageImage (task 5a)
- scanned/image-based/multi-page PDF → one rendered image per page via
  PyMuPDF (task 5b)
- the original upload is copied byte-for-byte into originals/ and never
  modified again; rendered pages live in rendered/
- unsupported formats are rejected with a clear error and no state is created
- all later bounding boxes use rendered-page pixel coordinates

The state machine advances UPLOADED → NORMALIZED after this stage.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from config import CONFIG
from schemas import DocumentSource, PageImage
from storage import StorageLayout

SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
SUPPORTED_EXTENSIONS = SUPPORTED_IMAGE_EXTENSIONS | {".pdf"}


class UnsupportedFormatError(ValueError):
    """Raised for any input that is not PNG/JPG/JPEG/WEBP/PDF."""


def classify_input(source_path: Path) -> str:
    """Return 'image' or 'pdf'; raise UnsupportedFormatError otherwise."""
    ext = Path(source_path).suffix.lower()
    if ext == ".pdf":
        return "pdf"
    if ext in SUPPORTED_IMAGE_EXTENSIONS:
        return "image"
    raise UnsupportedFormatError(
        f"Unsupported input format {ext or '(no extension)'}: "
        f"accepted formats are PNG, JPG, JPEG, WEBP, PDF"
    )


def _image_dpi(pil_image) -> int:
    """DPI from image metadata, falling back to the configured default."""
    dpi = pil_image.info.get("dpi")
    if dpi:
        try:
            value = dpi[0] if isinstance(dpi, (tuple, list)) else dpi
            value = int(round(float(value)))
            if value > 0:
                return value
        except (TypeError, ValueError):
            pass
    return CONFIG.ingestion.render_dpi


def _ingest_image(source_path: Path, layout: StorageLayout) -> list[PageImage]:
    """Task 5a: normalize one image file into a single PageImage."""
    from PIL import Image  # heavy dep imported lazily

    layout.ensure_page(1)
    rendered_path = layout.rendered_path(1)

    with Image.open(source_path) as img:
        width, height = img.size
        dpi = _image_dpi(img)
        # Rendered page = the input image re-encoded as PNG so every
        # downstream stage sees one uniform format.
        img.convert("RGB").save(rendered_path, format="PNG")

    return [
        PageImage(
            pageNumber=1,
            path=layout.rel(rendered_path),
            width=width,
            height=height,
            dpi=dpi,
        )
    ]


def _ingest_pdf(source_path: Path, layout: StorageLayout) -> list[PageImage]:
    """Task 5b: render every PDF page to an image at the configured DPI."""
    import pymupdf  # PyMuPDF

    layout.rendered.mkdir(parents=True, exist_ok=True)
    pages: list[PageImage] = []

    with pymupdf.open(source_path) as doc:
        if doc.is_encrypted:
            raise ValueError(f"Encrypted PDFs are not supported: {source_path.name}")
        zoom = CONFIG.ingestion.render_dpi / 72.0  # PDF native unit is 72 dpi
        matrix = pymupdf.Matrix(zoom, zoom)
        for index in range(len(doc)):
            page_number = index + 1
            layout.ensure_page(page_number)
            pixmap = doc.load_page(index).get_pixmap(matrix=matrix, alpha=False)
            rendered_path = layout.rendered_path(page_number)
            pixmap.save(str(rendered_path))
            pages.append(
                PageImage(
                    pageNumber=page_number,
                    path=layout.rel(rendered_path),
                    width=pixmap.width,
                    height=pixmap.height,
                    dpi=CONFIG.ingestion.render_dpi,
                )
            )

    if not pages:
        raise ValueError(f"PDF contains no pages: {source_path.name}")
    return pages


def ingest_document(source_path: Path, layout: StorageLayout) -> tuple[DocumentSource, list[PageImage]]:
    """Normalize an uploaded document into PageImages.

    Copies the original byte-for-byte into originals/ first, then renders.
    Returns the DocumentSource metadata and the ordered page list.

    Raises UnsupportedFormatError before any state is created for bad input.
    """
    source_path = Path(source_path)
    if not source_path.exists():
        raise FileNotFoundError(f"Input file does not exist: {source_path}")

    doc_type = classify_input(source_path)  # raises for unsupported formats

    layout.ensure_all()
    original_path = layout.original_path(source_path.name)
    shutil.copyfile(source_path, original_path)  # byte-for-byte preservation

    if doc_type == "pdf":
        pages = _ingest_pdf(original_path, layout)
    else:
        pages = _ingest_image(original_path, layout)

    return DocumentSource(type=doc_type, originalPath=layout.rel(original_path)), pages
