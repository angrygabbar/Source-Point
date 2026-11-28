import hashlib
import io
import os
import re
import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from functools import lru_cache

import boto3
import filetype
from botocore.client import Config
from botocore.exceptions import ClientError
from fastapi import UploadFile

from app.core.config import settings
from app.core.errors import IntegrationUnavailable, ValidationFailed
from app.core.logging import get_logger

log = get_logger(__name__)

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._ -]+")
# Extensions whose binary signature must match the declared type when detectable.
_EXECUTABLE_MIMES = {"application/x-msdownload", "application/x-executable", "application/x-elf", "application/x-mach-binary",
                     "application/x-sh", "application/vnd.microsoft.portable-executable"}


@dataclass
class StoredObject:
    object_key: str
    original_filename: str
    mime_type: str
    size_bytes: int
    checksum_sha256: str


@lru_cache
def client():
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT or None,
        aws_access_key_id=settings.S3_ACCESS_KEY or None,
        aws_secret_access_key=settings.S3_SECRET_KEY or None,
        region_name=settings.S3_REGION,
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}, retries={"max_attempts": 3}),
    )


def ensure_bucket() -> None:
    try:
        client().head_bucket(Bucket=settings.S3_BUCKET)
    except ClientError:
        client().create_bucket(Bucket=settings.S3_BUCKET)
        log.info("created object storage bucket")
    try:
        client().put_bucket_versioning(Bucket=settings.S3_BUCKET, VersioningConfiguration={"Status": "Enabled"})
    except ClientError:
        log.warning("bucket versioning could not be enabled")


def safe_filename(name: str | None) -> str:
    name = os.path.basename(name or "file")
    name = _SAFE_NAME.sub("_", name).strip(" .") or "file"
    return name[:200]


def validate_and_read(upload: UploadFile, allowed: set[str] | None = None, max_mb: int | None = None) -> tuple[bytes, str, str]:
    filename = safe_filename(upload.filename)
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if not ext:
        raise ValidationFailed("Files must have an extension")
    if ext in settings.blocked_extensions:
        raise ValidationFailed(f"File type .{ext} is not allowed")
    if ext not in (allowed or settings.allowed_extensions):
        raise ValidationFailed(f"File type .{ext} is not permitted")
    limit = (max_mb or settings.MAX_UPLOAD_MB) * 1024 * 1024
    data = upload.file.read(limit + 1)
    if len(data) > limit:
        raise ValidationFailed(f"File exceeds the {max_mb or settings.MAX_UPLOAD_MB} MB limit")
    if not data:
        raise ValidationFailed("File is empty")
    kind = filetype.guess(data[:8192])
    if kind is not None:
        if kind.mime in _EXECUTABLE_MIMES:
            raise ValidationFailed("Executable content is not allowed")
        office_zip = ext in {"docx", "xlsx", "pptx", "odt", "ods", "odp", "zip"} and kind.extension == "zip"
        if kind.extension != ext and not office_zip and not (ext in {"jpg", "jpeg"} and kind.extension in {"jpg", "jpeg"}):
            # Allow known aliases; otherwise reject spoofed extensions.
            if not (ext in {"m4a", "mp4"} and kind.extension in {"mp4", "m4a"}):
                raise ValidationFailed("File content does not match its extension")
        mime = kind.mime
    else:
        if data[:2] == b"MZ" or data[:4] == b"\x7fELF":
            raise ValidationFailed("Executable content is not allowed")
        mime = upload.content_type or "application/octet-stream"
        if ext in {"txt", "csv"}:
            mime = "text/csv" if ext == "csv" else "text/plain"
    return data, filename, mime


def put_bytes(institute_id: uuid.UUID, prefix: str, filename: str, data: bytes, mime: str) -> StoredObject:
    checksum = hashlib.sha256(data).hexdigest()
    key = f"{institute_id}/{prefix}/{uuid.uuid4()}/{filename}"
    try:
        client().put_object(
            Bucket=settings.S3_BUCKET,
            Key=key,
            Body=data,
            ContentType=mime,
            Metadata={"sha256": checksum},
        )
    except Exception as exc:  # noqa: BLE001
        log.error("object storage upload failed", extra={"ctx": {"error": type(exc).__name__}})
        raise IntegrationUnavailable("File storage is currently unavailable")
    return StoredObject(key, filename, mime, len(data), checksum)


def store_upload(institute_id: uuid.UUID, prefix: str, upload: UploadFile, allowed: set[str] | None = None) -> StoredObject:
    data, filename, mime = validate_and_read(upload, allowed)
    return put_bytes(institute_id, prefix, filename, data, mime)


def iter_object(key: str, chunk: int = 1024 * 256) -> Iterator[bytes]:
    try:
        obj = client().get_object(Bucket=settings.S3_BUCKET, Key=key)
    except ClientError:
        raise IntegrationUnavailable("File is not available in storage")
    body = obj["Body"]
    while True:
        data = body.read(chunk)
        if not data:
            break
        yield data


def get_bytes(key: str) -> bytes:
    return b"".join(iter_object(key))


def bytes_io(data: bytes) -> io.BytesIO:
    return io.BytesIO(data)


def bucket_usage_bytes(institute_id: uuid.UUID) -> int:
    total = 0
    paginator = client().get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=settings.S3_BUCKET, Prefix=f"{institute_id}/"):
        total += sum(o["Size"] for o in page.get("Contents", []))
    return total


def ping() -> bool:
    try:
        client().head_bucket(Bucket=settings.S3_BUCKET)
        return True
    except Exception:  # noqa: BLE001
        return False
