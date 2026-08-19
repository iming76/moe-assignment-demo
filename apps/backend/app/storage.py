"""Storage layout helpers (task 4).

Spec Section 37 directory structure:

    storage/
    ├── originals/
    ├── rendered/
    ├── processed/<page>/
    ├── crops/<page>/<type>/
    ├── ocr/<page>/
    └── output/

All paths recorded in metadata are relative to the storage root so documents
stay portable. The filesystem is the POC database.
"""

from __future__ import annotations

from pathlib import Path

from .config import CONFIG

# Crop type → subdirectory name under crops/<page>/ (spec Section 20).
CROP_TYPE_DIRS = {
    "question": "questions",
    "answer": "answers",
    "paragraph": "paragraphs",
    "line": "lines",
    "word": "words",
}

TOP_LEVEL_DIRS = ("originals", "rendered", "processed", "crops", "ocr", "output")


def page_dir_name(page_number: int) -> str:
    """page_001 style directory name."""
    return f"page_{page_number:03d}"


class StorageLayout:
    """Resolves artifact paths for one document within the storage root."""

    def __init__(self, document_id: str, root: str | Path | None = None) -> None:
        base = Path(root) if root is not None else Path(CONFIG.storage.root)
        self.root = base.resolve()
        self.document_id = document_id
        self.doc_root = self.root / document_id

    # -- top level ----------------------------------------------------------

    @property
    def originals(self) -> Path:
        return self.doc_root / "originals"

    @property
    def rendered(self) -> Path:
        return self.doc_root / "rendered"

    @property
    def output(self) -> Path:
        return self.doc_root / "output"

    # -- per-page ------------------------------------------------------------

    def processed_page(self, page_number: int) -> Path:
        return self.doc_root / "processed" / page_dir_name(page_number)

    def crops_page(self, page_number: int) -> Path:
        return self.doc_root / "crops" / page_dir_name(page_number)

    def crops_type(self, page_number: int, crop_type: str) -> Path:
        subdir = CROP_TYPE_DIRS.get(crop_type)
        if subdir is None:
            raise ValueError(f"Unknown crop type: {crop_type!r}")
        return self.crops_page(page_number) / subdir

    def ocr_page(self, page_number: int) -> Path:
        return self.doc_root / "ocr" / page_dir_name(page_number)

    # -- standard artifact paths ---------------------------------------------

    def original_path(self, filename: str) -> Path:
        return self.originals / filename

    def rendered_path(self, page_number: int) -> Path:
        return self.rendered / f"{page_dir_name(page_number)}.png"

    def crop_path(self, page_number: int, crop_type: str, crop_id: str) -> Path:
        return self.crops_type(page_number, crop_type) / f"{crop_id}.png"

    def ocr_json_path(self, page_number: int, unit_id: str) -> Path:
        return self.ocr_page(page_number) / f"{unit_id}.json"

    def output_json_path(self) -> Path:
        return self.output / "document.json"

    # -- creation -------------------------------------------------------------

    def ensure_all(self) -> None:
        """Create the full tree: top-level + output dirs.

        Per-page dirs are created on demand via ensure_page().
        """
        for name in TOP_LEVEL_DIRS:
            (self.doc_root / name).mkdir(parents=True, exist_ok=True)

    def ensure_page(self, page_number: int) -> None:
        """Create all per-page directories for one page."""
        self.rendered.mkdir(parents=True, exist_ok=True)
        self.processed_page(page_number).mkdir(parents=True, exist_ok=True)
        for crop_type in CROP_TYPE_DIRS:
            self.crops_type(page_number, crop_type).mkdir(parents=True, exist_ok=True)
        self.ocr_page(page_number).mkdir(parents=True, exist_ok=True)
        self.output.mkdir(parents=True, exist_ok=True)

    # -- portable relative paths ----------------------------------------------

    def rel(self, path: Path) -> str:
        """Path relative to the doc root, as recorded in metadata/JSON."""
        return str(Path(path).resolve().relative_to(self.doc_root))


def write_crop(layout: StorageLayout, page_number: int, crop_type: str, crop_id: str,
               image_bytes: bytes) -> Path:
    """Write one crop image. Returns the absolute path.

    Immutability rule (spec Section 21): refuses to overwrite an existing crop.
    """
    path = layout.crop_path(page_number, crop_type, crop_id)
    if path.exists():
        raise FileExistsError(f"Crop is immutable once written: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(image_bytes)
    return path
