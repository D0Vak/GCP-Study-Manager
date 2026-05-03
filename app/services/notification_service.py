import logging
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models.attendance import AttendanceStatus
from app.models.event import Event, EventStatus
from app.models.team import TeamMember

logger = logging.getLogger(__name__)
LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"
LINE_REPLY_URL = "https://api.line.me/v2/bot/message/reply"

JST = timezone(timedelta(hours=9))


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.line_channel_access_token}",
        "Content-Type": "application/json",
    }


def _push_text(to: str, text: str) -> None:
    if not settings.line_channel_access_token:
        logger.info("[LINE skip – no token] to=%s | %s", to, text)
        return
    try:
        with httpx.Client(timeout=10) as client:
            client.post(LINE_PUSH_URL, headers=_headers(), json={
                "to": to,
                "messages": [{"type": "text", "text": text}],
            }).raise_for_status()
    except Exception as exc:
        logger.error("LINE push error to=%s: %s", to, exc)


def _push_flex(to: str, alt_text: str, flex_content: dict) -> None:
    if not settings.line_channel_access_token:
        logger.info("[LINE skip – no token] to=%s | alt=%s", to, alt_text)
        return
    try:
        with httpx.Client(timeout=10) as client:
            client.post(LINE_PUSH_URL, headers=_headers(), json={
                "to": to,
                "messages": [{"type": "flex", "altText": alt_text, "contents": flex_content}],
            }).raise_for_status()
    except Exception as exc:
        logger.error("LINE flex push error to=%s: %s", to, exc)


def reply_text(reply_token: str, text: str) -> None:
    """Webhookのreplyトークンで返信。Push APIと違いメッセージ数にカウントされない"""
    if not settings.line_channel_access_token or not reply_token:
        return
    try:
        with httpx.Client(timeout=10) as client:
            client.post(LINE_REPLY_URL, headers=_headers(), json={
                "replyToken": reply_token,
                "messages": [{"type": "text", "text": text}],
            }).raise_for_status()
    except Exception as exc:
        logger.error("LINE reply error: %s", exc)


def _fmt_jst(dt: datetime) -> str:
    """ナイーブdatetimeをJST表示にフォーマット（DBにはJSTで保存されている前提）"""
    return dt.strftime("%Y/%m/%d(%a) %H:%M").replace(
        "Mon", "月").replace("Tue", "火").replace("Wed", "水").replace(
        "Thu", "木").replace("Fri", "金").replace("Sat", "土").replace("Sun", "日")


def _build_event_flex(event: Event) -> dict:
    """出欠ボタン付きFlex Messageバブルを構築"""
    date_str = _fmt_jst(event.scheduled_at)
    return {
        "type": "bubble",
        "size": "kilo",
        "header": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": "#4f46e5",
            "paddingAll": "12px",
            "contents": [
                {"type": "text", "text": "📚 イベントのお知らせ", "color": "#ffffff",
                 "size": "xs", "weight": "bold"}
            ],
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "paddingAll": "16px",
            "contents": [
                {"type": "text", "text": event.title, "weight": "bold",
                 "size": "lg", "wrap": True, "color": "#1f2937"},
                {"type": "text", "text": f"📅 {date_str}", "size": "sm",
                 "color": "#6b7280", "margin": "md"},
                {"type": "text", "text": "出欠をご回答ください", "size": "sm",
                 "color": "#9ca3af", "margin": "sm"},
            ],
        },
        "footer": {
            "type": "box",
            "layout": "horizontal",
            "spacing": "sm",
            "paddingAll": "12px",
            "contents": [
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#10b981",
                    "height": "sm",
                    "action": {
                        "type": "postback",
                        "label": "✓ 参加する",
                        "data": f"action=attend&event_id={event.id}&status=yes",
                    },
                },
                {
                    "type": "button",
                    "style": "primary",
                    "color": "#ef4444",
                    "height": "sm",
                    "action": {
                        "type": "postback",
                        "label": "✗ 欠席する",
                        "data": f"action=attend&event_id={event.id}&status=no",
                    },
                },
            ],
        },
    }


def _members(db: Session, team_id: int) -> list:
    return [m.user for m in db.query(TeamMember).filter_by(team_id=team_id).all()]


def send_reminder(db: Session, event: Event) -> None:
    alt = f"【出欠確認】{event.title} {_fmt_jst(event.scheduled_at)}"
    flex = _build_event_flex(event)
    if event.team.line_group_id:
        _push_flex(event.team.line_group_id, alt, flex)
    else:
        for user in _members(db, event.team_id):
            if user.line_id:
                _push_flex(user.line_id, alt, flex)
            else:
                logger.info("[reminder] %s: %s", user.name, alt)


def send_no_response(db: Session, event: Event) -> None:
    from app.models.attendance import Attendance

    responded = {
        r.user_id
        for r in db.query(Attendance).filter(
            Attendance.event_id == event.id,
            Attendance.status != AttendanceStatus.PENDING,
        ).all()
    }
    targets = [u for u in _members(db, event.team_id) if u.id not in responded]
    if not targets:
        return

    names = "、".join(u.name for u in targets)
    body = (
        f"【出欠未回答のお知らせ】{event.title}\n"
        f"📅 {_fmt_jst(event.scheduled_at)}\n\n"
        f"以下のメンバーがまだ回答していません:\n{names}\n\n"
        f"届いているリマインドメッセージのボタンから回答してください。"
    )
    if event.team.line_group_id:
        # グループに1通送るだけ（API枠を節約）
        _push_text(event.team.line_group_id, body)
    else:
        for user in targets:
            if user.line_id:
                _push_text(user.line_id, (
                    f"【出欠未回答】{event.title}\n"
                    f"📅 {_fmt_jst(event.scheduled_at)}\n"
                    f"まだ出欠が未回答です。ご確認ください。"
                ))
            else:
                logger.info("[no-response] %s", user.name)


def send_summary(db: Session, event: Event) -> None:
    from app.models.attendance import Attendance

    records = db.query(Attendance).filter_by(event_id=event.id).all()
    status_map: dict[int, AttendanceStatus] = {r.user_id: r.status for r in records}
    members = _members(db, event.team_id)

    yes = [u.name for u in members if status_map.get(u.id) == AttendanceStatus.YES]
    no = [u.name for u in members if status_map.get(u.id) == AttendanceStatus.NO]
    pending = [u.name for u in members if status_map.get(u.id, AttendanceStatus.PENDING) == AttendanceStatus.PENDING]

    body = (
        f"【出欠サマリー】{event.title}\n"
        f"📅 {_fmt_jst(event.scheduled_at)}\n\n"
        f"✅ 参加({len(yes)}): {', '.join(yes) or 'なし'}\n"
        f"❌ 不参加({len(no)}): {', '.join(no) or 'なし'}\n"
        f"⏳ 未回答({len(pending)}): {', '.join(pending) or 'なし'}"
    )
    if event.team.line_group_id:
        _push_text(event.team.line_group_id, body)
    else:
        sent: set[str] = set()
        for user in members:
            if user.line_id and user.line_id not in sent:
                _push_text(user.line_id, body)
                sent.add(user.line_id)
            elif not user.line_id:
                logger.info("[summary] %s: %s", user.name, body)


def send_event_created(db: Session, event: Event) -> None:
    alt = f"【新しいイベント】{event.title} {_fmt_jst(event.scheduled_at)}"
    flex = _build_event_flex(event)
    if event.team.line_group_id:
        _push_flex(event.team.line_group_id, alt, flex)
    else:
        for user in _members(db, event.team_id):
            if user.line_id:
                _push_flex(user.line_id, alt, flex)
            else:
                logger.info("[event_created] %s: %s", user.name, alt)


def send_custom(db: Session, team, message: str) -> None:
    if team.line_group_id:
        _push_text(team.line_group_id, message)
    else:
        sent: set[str] = set()
        for user in _members(db, team.id):
            if user.line_id and user.line_id not in sent:
                _push_text(user.line_id, message)
                sent.add(user.line_id)
            elif not user.line_id:
                logger.info("[custom] %s: %s", user.name, message)


def run_daily_reminders() -> None:
    """毎日 09:00 JST 実行想定 — 翌日のイベントにリマインド送信"""
    db: Session = SessionLocal()
    try:
        # DBの日時はJST入力前提なので、UTC+9でオフセット計算
        now_jst = datetime.utcnow() + timedelta(hours=9)
        tomorrow_start = (now_jst + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        tomorrow_end = tomorrow_start + timedelta(days=1)
        events = (
            db.query(Event)
            .filter(
                Event.status == EventStatus.SCHEDULED,
                Event.scheduled_at >= tomorrow_start,
                Event.scheduled_at < tomorrow_end,
            )
            .all()
        )
        for event in events:
            logger.info("daily reminder: event_id=%d title=%s", event.id, event.title)
            send_reminder(db, event)
    finally:
        db.close()
