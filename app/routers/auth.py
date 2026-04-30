import secrets

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.jwt_utils import create_token
from app.auth.line_oauth import build_auth_url, exchange_code, get_profile
from app.config import settings
from app.database import get_db
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])

_pending_states: set[str] = set()


@router.get("/mode")
def auth_mode():
    return {"auth_enabled": settings.auth_enabled}


@router.get("/line")
def line_login():
    if not settings.auth_enabled:
        raise HTTPException(status_code=503, detail="LINE Login is not configured")
    state = secrets.token_urlsafe(16)
    _pending_states.add(state)
    return RedirectResponse(build_auth_url(state))


@router.get("/callback")
def line_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
):
    if state not in _pending_states:
        raise HTTPException(status_code=400, detail="Invalid or expired state")
    _pending_states.discard(state)

    try:
        token_data = exchange_code(code)
        profile = get_profile(token_data["access_token"])
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"LINE OAuth error: {exc}")

    line_id: str = profile["userId"]
    name: str = profile.get("displayName", "LINEユーザー")

    # Upsert: 既存ユーザーは名前を更新、新規は作成
    user = db.query(User).filter(User.line_id == line_id).first()
    if not user:
        user = User(name=name, line_id=line_id)
        db.add(user)
    else:
        user.name = name
    db.commit()
    db.refresh(user)

    jwt_token = create_token(user.id, None, user.name)
    return RedirectResponse(f"/?token={jwt_token}")


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "name": current_user.name,
        "line_id": current_user.line_id,
    }
