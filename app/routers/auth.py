import secrets

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.auth.google_oauth import build_auth_url, exchange_code, get_userinfo
from app.auth.jwt_utils import create_token
from app.config import settings
from app.database import get_db
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])

# In-memory CSRF state store (single-instance OK; use Redis for multi-instance)
_pending_states: set[str] = set()


@router.get("/mode")
def auth_mode():
    """フロントエンドが認証モードを判断するための公開エンドポイント"""
    return {"auth_enabled": settings.auth_enabled}


@router.get("/google")
def google_login():
    if not settings.auth_enabled:
        raise HTTPException(status_code=503, detail="Google OAuth is not configured")
    state = secrets.token_urlsafe(16)
    _pending_states.add(state)
    return RedirectResponse(build_auth_url(state))


@router.get("/callback")
def google_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
):
    if state not in _pending_states:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")
    _pending_states.discard(state)

    try:
        token_data = exchange_code(code)
        userinfo = get_userinfo(token_data["access_token"])
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Google OAuth error: {exc}")

    google_id: str = userinfo["id"]
    email: str = userinfo.get("email", "")
    name: str = userinfo.get("name", email)

    # Upsert user
    user = db.query(User).filter(User.google_id == google_id).first()
    if not user and email:
        user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(name=name, email=email, google_id=google_id)
        db.add(user)
    else:
        user.google_id = google_id
        user.name = name
        if email:
            user.email = email
    db.commit()
    db.refresh(user)

    jwt_token = create_token(user.id, user.email, user.name)
    # Redirect to frontend — token in query param (frontend stores it and cleans URL)
    return RedirectResponse(f"/?token={jwt_token}")


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "line_id": current_user.line_id,
    }
