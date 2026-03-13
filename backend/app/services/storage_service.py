from __future__ import annotations

import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import BinaryIO, Optional, Tuple

import boto3
from botocore.client import Config as BotoConfig
from flask import current_app
from werkzeug.datastructures import FileStorage


ALLOWED_EXTENSIONS = {"pdf"}


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _normalise_filename(filename: Optional[str]) -> str:
    """Return a safe filename, falling back to a default."""
    name = filename or "paper.pdf"
    # Strip any directory components
    return os.path.basename(name)


def _workspace_object_key(workspace_id: str, filename: str) -> str:
    """Return the object key / relative path for a workspace file."""
    return f"uploads/{workspace_id}/{filename}"


def _get_s3_client():
    cfg = current_app.config
    session = boto3.session.Session()
    client = session.client(
        "s3",
        region_name=cfg.get("S3_REGION") or None,
        aws_access_key_id=cfg.get("S3_ACCESS_KEY_ID") or None,
        aws_secret_access_key=cfg.get("S3_SECRET_ACCESS_KEY") or None,
        endpoint_url=cfg.get("S3_ENDPOINT_URL") or None,
        config=BotoConfig(s3={"addressing_style": "virtual"}),
    )
    return client


def save_paper_file(file: FileStorage, workspace_id: str) -> Tuple[str, str]:
    """Store the uploaded PDF and return (filename, storage_path_or_key).

    In ``local`` mode this writes under ``UPLOAD_FOLDER`` on disk and returns a
    relative path such as ``uploads/<workspace>/<file>`` (backwards compatible
    with existing behaviour). In ``s3`` mode this uploads the object and
    returns the object key using the same convention.
    """
    provider = current_app.config.get("STORAGE_PROVIDER", "local").lower()
    filename = _normalise_filename(file.filename)

    if provider == "s3":
        object_key = _workspace_object_key(workspace_id, filename)
        client = _get_s3_client()
        bucket = current_app.config.get("S3_BUCKET_NAME")
        if not bucket:
            raise RuntimeError("S3_BUCKET_NAME must be set when STORAGE_PROVIDER='s3'")
        # Upload file stream directly
        file.stream.seek(0)
        client.upload_fileobj(file.stream, bucket, object_key)
        return filename, object_key

    # Default: local filesystem storage
    upload_root = Path(current_app.config["UPLOAD_FOLDER"])
    workspace_dir = upload_root / workspace_id
    workspace_dir.mkdir(parents=True, exist_ok=True)

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


def get_local_filesystem_path(storage_path_or_key: str) -> Path:
    """Resolve a stored relative path to an absolute local filesystem path.

    This is only valid when using the ``local`` storage provider.
    """
    upload_root = Path(current_app.config["UPLOAD_FOLDER"])
    # Existing behaviour stores paths relative to the backend root, e.g.
    # "uploads/<workspace>/<file>". Support both relative-to-root and
    # relative-to-uploads forms.
    rel = Path(storage_path_or_key)
    if rel.parts and rel.parts[0] != Path(upload_root).name:
        rel = Path(upload_root.name) / rel
    return upload_root.parent / rel


def open_paper_file_for_read(storage_path_or_key: str) -> BinaryIO:
    """Return a readable binary file-like for the stored paper.

    For local storage this opens the underlying file directly. For S3 this
    downloads the object to a temporary file and returns a handle positioned
    at the start. The caller is responsible for closing the handle; temporary
    files are deleted when closed.
    """
    provider = current_app.config.get("STORAGE_PROVIDER", "local").lower()

    if provider == "s3":
        client = _get_s3_client()
        bucket = current_app.config.get("S3_BUCKET_NAME")
        if not bucket:
            raise RuntimeError("S3_BUCKET_NAME must be set when STORAGE_PROVIDER='s3'")

        tmp = NamedTemporaryFile(mode="wb+", suffix=".pdf", delete=True)
        client.download_fileobj(bucket, storage_path_or_key, tmp)
        tmp.seek(0)
        return tmp

    # local
    path = get_local_filesystem_path(storage_path_or_key)
    return path.open("rb")


def delete_paper_file(storage_path_or_key: str) -> None:
    """Delete a stored paper file, if it exists."""
    provider = current_app.config.get("STORAGE_PROVIDER", "local").lower()
    if provider == "s3":
        client = _get_s3_client()
        bucket = current_app.config.get("S3_BUCKET_NAME")
        if not bucket:
            return
        client.delete_object(Bucket=bucket, Key=storage_path_or_key)
        return

    path = get_local_filesystem_path(storage_path_or_key)
    try:
        path.unlink()
    except FileNotFoundError:
        pass

