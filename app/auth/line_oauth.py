from urllib.parse import urlencode

import httpx

from app.config import settings

_AUTH_URL = "https://access.line.me/oauth2/v2.1/authorize"
_TOKEN_URL = "https://api.line.me/oauth2/v2.1/token"
_PROFILE_URL = "https://api.line.me/v2/profile"


def build_auth_url(state: str) -> str:
    params = {
        "response_type": "code",
        "client_id": settings.line_login_channel_id,
        "redirect_uri": settings.line_login_redirect_uri,
        "state": state,
        "scope": "profile openid",
    }
    return f"{_AUTH_URL}?{urlencode(params)}"


def exchange_code(code: str) -> dict:
    with httpx.Client(timeout=10) as client:
        resp = client.post(_TOKEN_URL, data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.line_login_redirect_uri,
            "client_id": settings.line_login_channel_id,
            "client_secret": settings.line_login_channel_secret,
        })
        resp.raise_for_status()
        return resp.json()


def get_profile(access_token: str) -> dict:
    with httpx.Client(timeout=10) as client:
        resp = client.get(_PROFILE_URL, headers={"Authorization": f"Bearer {access_token}"})
        resp.raise_for_status()
        return resp.json()
