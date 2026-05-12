import hashlib
import hmac
import secrets
import time

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

_STATE_TTL = 600  # 10 minutes


def _create_state() -> str:
    nonce = secrets.token_urlsafe(16)
    ts = str(int(time.time()))
    payload = f"{nonce}.{ts}"
    sig = hmac.new(settings.jwt_secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"


def _verify_state(state: str) -> bool:
    try:
        nonce, ts, sig = state.rsplit(".", 2)
        payload = f"{nonce}.{ts}"
        expected = hmac.new(settings.jwt_secret_key.encode(), payload.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return False
        return int(time.time()) - int(ts) <= _STATE_TTL
    except Exception:
        return False


@router.get("/mode")
def auth_mode():
    return {"auth_enabled": settings.auth_enabled}


@router.get("/line")
def line_login():
    if not settings.auth_enabled:
        raise HTTPException(status_code=503, detail="LINE Login is not configured")
    return RedirectResponse(build_auth_url(_create_state()))


@router.get("/callback")
def line_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
):
    if not _verify_state(state):
        raise HTTPException(status_code=400, detail="Invalid or expired state")

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
