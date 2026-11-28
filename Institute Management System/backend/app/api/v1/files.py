import uuid

import jwt
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.errors import Forbidden
from app.core.security import create_signed_token, decode_token
from app.db.session import get_db
from app.models import FileDownloadLog
from app.services import storage

router = APIRouter(tags=["Files"])

INLINE_MIMES = {"image/png", "image/jpeg", "image/gif", "image/webp", "video/mp4", "video/webm", "audio/mpeg"}


def download_url(
    p,
    object_key: str,
    filename: str,
    mime: str,
    object_type: str,
    object_id: uuid.UUID,
    version_id: uuid.UUID | None = None,
    minutes: int = 5,
) -> str:
    token = create_signed_token(
        {
            "k": object_key,
            "n": filename,
            "m": mime,
            "u": str(p.user_id) if p.user_id else None,
            "i": str(p.institute_id),
            "ot": object_type,
            "oid": str(object_id),
            "vid": str(version_id) if version_id else None,
        },
        minutes,
        "dl",
    )
    return f"/api/v1/files/{token}"


@router.get("/files/{token}", include_in_schema=True, summary="Download a file through a short-lived signed link")
def download(token: str, request: Request, inline: bool = False, db: Session = Depends(get_db)):
    try:
        data = decode_token(token, "dl")
    except jwt.PyJWTError:
        raise Forbidden("Download link is invalid or expired")
    if not str(data["k"]).startswith(f"{data['i']}/"):
        raise Forbidden("Invalid download link")
    db.add(
        FileDownloadLog(
            institute_id=uuid.UUID(data["i"]),
            user_id=uuid.UUID(data["u"]) if data.get("u") else None,
            object_type=data["ot"],
            object_id=uuid.UUID(data["oid"]),
            version_id=uuid.UUID(data["vid"]) if data.get("vid") else None,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent", "")[:500],
        )
    )
    db.commit()
    mime = data.get("m") or "application/octet-stream"
    disp = "inline" if inline and mime in INLINE_MIMES else "attachment"
    name = str(data.get("n") or "file").replace('"', "")
    return StreamingResponse(
        storage.iter_object(data["k"]),
        media_type=mime,
        headers={"Content-Disposition": f'{disp}; filename="{name}"', "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
    )
