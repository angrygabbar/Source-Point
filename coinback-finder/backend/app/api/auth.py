from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.database.models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/me")
def me(user: User = Depends(get_current_user)) -> dict:
    """Return the SourcePoint administrator currently using this module."""
    return {"data": {"id": user.id, "username": user.username}}
