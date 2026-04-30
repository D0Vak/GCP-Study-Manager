from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.attendance import AttendanceResponse, AttendanceUpdate
from app.schemas.user import UserResponse
from app.services import attendance_service, notification_service

router = APIRouter(prefix="/events/{event_id}/attendances", tags=["出欠"])


@router.get("", response_model=list[AttendanceResponse])
def list_attendance(event_id: int, db: Session = Depends(get_db)):
    return attendance_service.list_attendance(db, event_id)


@router.put("/{user_id}", response_model=AttendanceResponse)
def update_attendance(event_id: int, user_id: int, data: AttendanceUpdate, db: Session = Depends(get_db)):
    return attendance_service.update_attendance(db, event_id, user_id, data.status)


@router.get("/no-response", response_model=list[UserResponse])
def get_no_response_users(event_id: int, db: Session = Depends(get_db)):
    return attendance_service.get_no_response_users(db, event_id)


@router.post("/notify/reminder")
def notify_reminder(event_id: int, db: Session = Depends(get_db)):
    records = attendance_service.list_attendance(db, event_id)
    if not records:
        return {"message": "対象なし"}
    event = records[0].event
    notification_service.send_reminder_for_event(db, event)
    return {"message": "リマインド通知を送信しました"}


@router.post("/notify/no-response")
def notify_no_response(event_id: int, db: Session = Depends(get_db)):
    records = attendance_service.list_attendance(db, event_id)
    if not records:
        return {"message": "対象なし"}
    event = records[0].event
    notification_service.send_no_response_reminder(db, event)
    return {"message": "未回答者への通知を送信しました"}


@router.post("/notify/summary")
def notify_summary(event_id: int, db: Session = Depends(get_db)):
    records = attendance_service.list_attendance(db, event_id)
    if not records:
        return {"message": "対象なし"}
    event = records[0].event
    notification_service.send_attendance_summary(db, event)
    return {"message": "出欠状況を共有しました"}
