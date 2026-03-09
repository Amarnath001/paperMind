from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple

from flask import current_app
from werkzeug.datastructures import FileStorage


ALLOWED_EXTENSIONS = {"pdf"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_paper_file(file: FileStorage, workspace_id: str) -> Tuple[str, str]:
    """Save uploaded PDF under the uploads directory.

    Returns (filename, relative_path).
    """
    upload_root = Path(current_app.config["UPLOAD_FOLDER"])
    workspace_dir = upload_root / workspace_id
    workspace_dir.mkdir(parents=True, exist_ok=True)

    filename = file.filename or "paper.pdf"
    filename = os.path.basename(filename)
    target_path = workspace_dir / filename

    # Avoid clobbering existing files
    counter = 1
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    while target_path.exists():
        filename = f"{stem}_{counter}{suffix}"
        target_path = workspace_dir / filename
        counter += 1

    file.save(target_path)

    # Store relative path from backend root (e.g. "uploads/<workspace>/<file>")
    relative_path = str(target_path.relative_to(upload_root.parent))
    return filename, relative_path

