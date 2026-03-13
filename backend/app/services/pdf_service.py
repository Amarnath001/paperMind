from __future__ import annotations

from pathlib import Path
from typing import Optional
from pypdf import PdfReader

from app.config import Config
from app.services.storage_service import (
    get_local_filesystem_path,
    open_paper_file_for_read,
)


def _extract_text_from_reader(reader: PdfReader) -> str:
    """Extract concatenated text from a PdfReader instance."""
    parts: list[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text:
            parts.append(text)

    return "\n".join(parts).strip()


def extract_text_from_pdf(path_or_key: str, *, storage_managed: bool = False) -> str:
    """Extract text from a PDF file.

    When ``storage_managed`` is False (legacy behaviour), ``path_or_key`` is
    treated as a filesystem path. When True, it is treated as the stored
    ``file_path`` / object key and resolved via the storage abstraction,
    supporting both local and S3-backed storage.
    """
    if not storage_managed:
        pdf_path = Path(path_or_key)
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found at {pdf_path}")
        reader = PdfReader(str(pdf_path))
        return _extract_text_from_reader(reader)

    provider = Config.STORAGE_PROVIDER.lower()
    if provider == "s3":
        # Fetch via storage abstraction (downloads to a temp file)
        with open_paper_file_for_read(path_or_key) as fh:
            reader = PdfReader(fh)
            return _extract_text_from_reader(reader)

    # local managed mode – resolve relative storage path to absolute path
    pdf_path = get_local_filesystem_path(path_or_key)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found at {pdf_path}")
    reader = PdfReader(str(pdf_path))
    return _extract_text_from_reader(reader)

