from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.attendance import Attendance, AttendanceStatus
from app.models.team import TeamMember
from app.models.user import User
from app.schemas.attendance import AttendanceRecord, AttendanceUpsert
from app.services.event_service import get_event_or_404


def _get_team_members(db: Session, team_id: int) -> list[User]:
    return [m.user for m in db.query(TeamMember).filter_by(team_id=team_id).all()]


def upsert_attendance(db: Session, event_id: int, data: AttendanceUpsert) -> AttendanceRecord:
    event = get_event_or_404(db, event_id)
    user = db.get(User, data.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")

    # チームメンバーか確認
    if not db.query(TeamMember).filter_by(team_id=event.team_id, user_id=data.user_id).first():
        raise HTTPException(status_code=400, detail="このユーザーはチームのメンバーではありません")

    record = db.query(Attendance).filter_by(event_id=event_id, user_id=data.user_id).first()
    if record:
        record.status = data.status
    else:
        record = Attendance(event_id=event_id, user_id=data.user_id, status=data.status)
        db.add(record)
    db.commit()
    db.refresh(record)
    return AttendanceRecord(user=user, status=record.status)


def list_attendance(db: Session, event_id: int) -> list[AttendanceRecord]:
    """全チームメンバーを返す。Attendanceレコードがなければ pending として扱う"""
    event = get_event_or_404(db, event_id)
    members = _get_team_members(db, event.team_id)

    existing: dict[int, AttendanceStatus] = {
        r.user_id: r.status
        for r in db.query(Attendance).filter_by(event_id=event_id).all()
    }

    return [
        AttendanceRecord(user=m, status=existing.get(m.id, AttendanceStatus.PENDING))
        for m in members
    ]


def list_no_response(db: Session, event_id: int) -> list[User]:
    """Attendanceレコードなし または status=pending のメンバーを返す"""
    event = get_event_or_404(db, event_id)
    members = _get_team_members(db, event.team_id)

    responded = {
        r.user_id
        for r in db.query(Attendance).filter(
            Attendance.event_id == event_id,
            Attendance.status != AttendanceStatus.PENDING,
        ).all()
    }

    return [m for m in members if m.id not in responded]
