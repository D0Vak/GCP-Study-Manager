"""
LINE Messaging API Webhook
- ボットがグループに招待されたとき、またはグループでメッセージが届いたとき
  に groupId を自動検出してメモリに保存する
- 検出した groupId は GET /webhook/line/groups で確認できる
"""
import base64
import hashlib
import hmac
import json
import logging

from fastapi import APIRouter, Header, HTTPException, Request

from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhook", tags=["webhook"])

# 検出した LINEグループID を一時保存（サーバー再起動で消えるが実用上は十分）
_detected_groups: dict[str, str] = {}  # groupId -> 検出方法メモ


def _verify_signature(body: bytes, signature: str) -> bool:
    secret = settings.line_messaging_channel_secret
    if not secret:
        return True  # シークレット未設定時は検証スキップ（開発用）
    digest = hmac.new(secret.encode(), body, hashlib.sha256).digest()
    return hmac.compare_digest(base64.b64encode(digest).decode(), signature)


@router.post("/line")
async def line_webhook(
    request: Request,
    x_line_signature: str = Header(default=""),
):
    body = await request.body()

    if not _verify_signature(body, x_line_signature):
        raise HTTPException(status_code=400, detail="Invalid signature")

    data = json.loads(body)
    for event in data.get("events", []):
        source = event.get("source", {})
        source_type = source.get("type")

        if source_type == "group":
            group_id = source["groupId"]
            event_type = event.get("type", "")
            _detected_groups[group_id] = f"type={event_type}"
            logger.info("LINE Group detected: %s (event=%s)", group_id, event_type)

        elif source_type == "user":
            # 個人チャットでのメッセージ（デバッグ用にログ）
            user_id = source.get("userId", "")
            logger.info("LINE User message: userId=%s", user_id)

    return {"status": "ok"}


@router.get("/line/groups")
def detected_groups():
    """Webhookで検出されたLINEグループIDの一覧を返す"""
    return [{"group_id": gid, "note": note} for gid, note in _detected_groups.items()]
