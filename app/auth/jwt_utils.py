from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException

from app.config import settings

_ALGORITHM = "HS256"


def create_token(user_id: int, email: str | None, name: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": str(user_id), "email": email or "", "name": name, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
