import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.attendance import AttendanceRecord, AttendanceUpsert
from app.schemas.event import EventCreate, EventResponse, EventStatusUpdate, EventUpdate
from app.schemas.user import UserResponse
from app.services import attendance_service, event_service, notification_service
from app.services.event_service import get_event_or_404
from app.services.team_service import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/events", tags=["events"], dependencies=[CurrentUser])


# ── Event CRUD ──────────────────────────────────────────────────────────────

@router.post("", response_model=EventResponse, status_code=201)
def create_event(data: EventCreate, db: Session = Depends(get_db)):
    event = event_service.create_event(db, data)
    try:
        notification_service.send_event_created(db, event)
    except Exception as exc:
        logger.error("send_event_created failed: %s", exc)
    return event


@router.get("", response_model=list[EventResponse])
def list_events(team_id: int | None = None, db: Session = Depends(get_db)):
    return event_service.list_events(db, team_id)


# NOTE: /next must be before /{event_id} to avoid route conflict
@router.get("/next", response_model=EventResponse | None)
def get_next_event(team_id: int, db: Session = Depends(get_db)):
    return event_service.get_next_event(db, team_id)


@router.patch("/{event_id}", response_model=EventResponse)
def update_event(event_id: int, data: EventUpdate, db: Session = Depends(get_db)):
    return event_service.update_event(db, event_id, data)


@router.patch("/{event_id}/status", response_model=EventResponse)
def update_status(event_id: int, data: EventStatusUpdate, db: Session = Depends(get_db)):
    return event_service.update_status(db, event_id, data.status)


@router.delete("/{event_id}", status_code=204)
def delete_event(
    event_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    event = get_event_or_404(db, event_id)
    require_admin(db, current_user.id, event.team_id)
    event_service.delete_event(db, event_id)


# ── Attendance ───────────────────────────────────────────────────────────────

@router.put("/{event_id}/attendance", response_model=AttendanceRecord)
def upsert_attendance(event_id: int, data: AttendanceUpsert, db: Session = Depends(get_db)):
    return attendance_service.upsert_attendance(db, event_id, data)


@router.get("/{event_id}/attendance", response_model=list[AttendanceRecord])
def list_attendance(event_id: int, db: Session = Depends(get_db)):
    return attendance_service.list_attendance(db, event_id)


@router.get("/{event_id}/attendance/no-response", response_model=list[UserResponse])
def list_no_response(event_id: int, db: Session = Depends(get_db)):
    return attendance_service.list_no_response(db, event_id)


# ── Notification ─────────────────────────────────────────────────────────────

@router.post("/{event_id}/notify/reminder")
def notify_reminder(event_id: int, db: Session = Depends(get_db)):
    event = get_event_or_404(db, event_id)
    notification_service.send_reminder(db, event)
    return {"message": "リマインドを送信しました"}


@router.post("/{event_id}/notify/no-response")
def notify_no_response(event_id: int, db: Session = Depends(get_db)):
    event = get_event_or_404(db, event_id)
    notification_service.send_no_response(db, event)
    return {"message": "未回答者に通知しました"}


@router.post("/{event_id}/notify/summary")
def notify_summary(event_id: int, db: Session = Depends(get_db)):
    event = get_event_or_404(db, event_id)
    notification_service.send_summary(db, event)
    return {"message": "サマリーを送信しました"}
