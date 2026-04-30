import logging
from datetime import datetime, timedelta

import httpx
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models.attendance import AttendanceStatus
from app.models.event import Event, EventStatus
from app.models.team import TeamMember

logger = logging.getLogger(__name__)
LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"


def _push(to: str, text: str) -> None:
    if not settings.line_channel_access_token:
        logger.info("[LINE skip – no token] to=%s | %s", to, text)
        return
    headers = {
        "Authorization": f"Bearer {settings.line_channel_access_token}",
        "Content-Type": "application/json",
    }
    try:
        with httpx.Client(timeout=10) as client:
            client.post(LINE_PUSH_URL, headers=headers, json={
                "to": to,
                "messages": [{"type": "text", "text": text}],
            }).raise_for_status()
    except Exception as exc:
        logger.error("LINE push error to=%s: %s", to, exc)


def _members(db: Session, team_id: int) -> list:
    return [m.user for m in db.query(TeamMember).filter_by(team_id=team_id).all()]


def send_reminder(db: Session, event: Event) -> None:
    body = (
        f"【勉強会リマインド】\n"
        f"{event.title}\n"
        f"日時: {event.scheduled_at.strftime('%Y/%m/%d %H:%M')}\n"
        f"明日開催です。出欠の確認をお願いします。"
    )
    if event.team.line_group_id:
        _push(event.team.line_group_id, body)
    else:
        for user in _members(db, event.team_id):
            if user.line_id:
                _push(user.line_id, body)
            else:
                logger.info("[reminder] %s: %s", user.name, body)


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
    body = (
        f"【出欠未回答】{event.title}\n"
        f"日時: {event.scheduled_at.strftime('%Y/%m/%d %H:%M')}\n"
        f"まだ出欠が未回答です。ご確認ください。"
    )
    for user in targets:
        if user.line_id:
            _push(user.line_id, body)
        else:
            logger.info("[no-response] %s: %s", user.name, body)


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
        f"参加({len(yes)}): {', '.join(yes) or 'なし'}\n"
        f"不参加({len(no)}): {', '.join(no) or 'なし'}\n"
        f"未回答({len(pending)}): {', '.join(pending) or 'なし'}"
    )
    if event.team.line_group_id:
        _push(event.team.line_group_id, body)
    else:
        sent: set[str] = set()
        for user in members:
            if user.line_id and user.line_id not in sent:
                _push(user.line_id, body)
                sent.add(user.line_id)
            elif not user.line_id:
                logger.info("[summary] %s: %s", user.name, body)


def run_daily_reminders() -> None:
    """毎日 09:00 JST 実行 — 翌日のイベントにリマインド送信"""
    db: Session = SessionLocal()
    try:
        tomorrow = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        events = (
            db.query(Event)
            .filter(
                Event.status == EventStatus.SCHEDULED,
                Event.scheduled_at >= tomorrow,
                Event.scheduled_at < tomorrow + timedelta(days=1),
            )
            .all()
        )
        for event in events:
            logger.info("daily reminder: event_id=%d title=%s", event.id, event.title)
            send_reminder(db, event)
    finally:
        db.close()
