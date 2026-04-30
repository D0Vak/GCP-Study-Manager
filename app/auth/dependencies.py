import logging

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth.jwt_utils import decode_token
from app.config import settings
from app.database import get_db
from app.models.user import User

logger = logging.getLogger(__name__)
_bearer = HTTPBearer(auto_error=False)

_DEV_EMAIL = "dev@localhost"


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> User:
    # ── Dev mode: Google OAuth 未設定時は自動でdevユーザーを返す ──
    if not settings.auth_enabled:
        user = db.query(User).filter(User.email == _DEV_EMAIL).first()
        if not user:
            user = User(name="Dev User", email=_DEV_EMAIL)
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = decode_token(credentials.credentials)
    user = db.get(User, int(payload["sub"]))
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


# Shorthand alias for use in route signatures
CurrentUser = Depends(get_current_user)
