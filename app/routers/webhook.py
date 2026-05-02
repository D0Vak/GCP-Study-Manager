"""
LINE Messaging API Webhook
- グループへの招待時に自動でグループIDをDBに保存
- グループ参加時（join）に歓迎メッセージとグループIDを送信
- postbackイベントで出欠を自動更新（Flex Messageのボタン押下）
"""
import base64
import hashlib
import hmac
import json
import logging
from urllib.parse import parse_qs

from fastapi import APIRouter, Header, HTTPException, Request

from app.config import settings
from app.database import SessionLocal
from app.models.detected_group import DetectedGroup

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhook", tags=["webhook"])


def _verify_signature(body: bytes, signature: str) -> bool:
    secret = settings.line_messaging_channel_secret
    if not secret:
        return True
    digest = hmac.new(secret.encode(), body, hashlib.sha256).digest()
    return hmac.compare_digest(base64.b64encode(digest).decode(), signature)


def _save_group(group_id: str, note: str) -> None:
    db = SessionLocal()
    try:
        existing = db.get(DetectedGroup, group_id)
        if not existing:
            db.add(DetectedGroup(group_id=group_id, note=note))
            db.commit()
    finally:
        db.close()


def _handle_postback(event: dict) -> None:
    """Flex Messageのボタン押下 → 出欠を自動更新してreplyで確認メッセージを返す"""
    from app.models.attendance import Attendance, AttendanceStatus
    from app.models.event import Event
    from app.models.team import TeamMember
    from app.models.user import User
    from app.services.notification_service import reply_text

    data_str = event.get("postback", {}).get("data", "")
    reply_token = event.get("replyToken", "")
    source = event.get("source", {})
    line_user_id = source.get("userId", "")

    # action=attend&event_id=N&status=yes|no
    try:
        params = dict(kv.split("=") for kv in data_str.split("&") if "=" in kv)
    except Exception:
        return

    if params.get("action") != "attend":
        return

    try:
        event_id = int(params["event_id"])
        status_str = params["status"]
    except (KeyError, ValueError):
        return

    if status_str not in ("yes", "no"):
        return

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.line_id == line_user_id).first()
        if not user:
            reply_text(reply_token, "ユーザーが見つかりません。先にWebアプリでLINEログインしてください。")
            return

        ev = db.get(Event, event_id)
        if not ev:
            reply_text(reply_token, "勉強会が見つかりません。")
            return

        if not db.query(TeamMember).filter_by(team_id=ev.team_id, user_id=user.id).first():
            reply_text(reply_token, "このチームのメンバーではありません。")
            return

        att_status = AttendanceStatus.YES if status_str == "yes" else AttendanceStatus.NO
        record = db.query(Attendance).filter_by(event_id=event_id, user_id=user.id).first()
        if record:
            record.status = att_status
        else:
            record = Attendance(event_id=event_id, user_id=user.id, status=att_status)
            db.add(record)
        db.commit()

        label = "参加" if status_str == "yes" else "欠席"
        reply_text(reply_token, f"{user.name}さん、「{ev.title}」への{label}を受け付けました！✅")
    finally:
        db.close()


def _handle_join(group_id: str, reply_token: str) -> None:
    """ボットがグループに招待されたとき、グループIDを含む案内を送る"""
    from app.services.notification_service import reply_text

    _save_group(group_id, "type=join")

    base_url = settings.app_base_url.rstrip("/") if settings.app_base_url else ""
    msg = (
        f"勉強会管理ボットが参加しました！📚\n\n"
        f"このグループのIDは\n{group_id}\nです。\n\n"
        f"管理画面の「チーム管理」→「LINEグループ連携」から"
        f"このIDをチームに連携してください。"
    )
    if base_url:
        msg += f"\n\n管理画面: {base_url}"
    reply_text(reply_token, msg)


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
        event_type = event.get("type", "")
        reply_token = event.get("replyToken", "")

        if source_type == "group":
            group_id = source["groupId"]

            if event_type == "join":
                _handle_join(group_id, reply_token)
            elif event_type == "postback":
                _handle_postback(event)
            elif event_type == "message":
                _save_group(group_id, f"type={event_type}")
                text = event.get("message", {}).get("text", "")
                if "グループID" in text:
                    from app.services.notification_service import reply_text
                    reply_text(reply_token, f"このグループのIDは\n{group_id}\nです。")
                else:
                    logger.info("LINE Group message: %s", group_id)
            else:
                _save_group(group_id, f"type={event_type}")
                logger.info("LINE Group event: %s (event=%s)", group_id, event_type)

        elif source_type == "user":
            if event_type == "postback":
                _handle_postback(event)
            else:
                logger.info("LINE User event: userId=%s type=%s", source.get("userId"), event_type)

    return {"status": "ok"}


@router.get("/line/groups")
def detected_groups():
    """DBに保存されたLINEグループIDの一覧を返す"""
    db = SessionLocal()
    try:
        groups = db.query(DetectedGroup).order_by(DetectedGroup.detected_at.desc()).all()
        return [{"group_id": g.group_id, "note": g.note} for g in groups]
    finally:
        db.close()
