from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.team import Team, TeamMember
from app.models.user import User
from app.schemas.team import TeamCreate, TeamRename, TeamUpdate


def is_team_admin(db: Session, user_id: int, team_id: int) -> bool:
    """管理者チェック。チームに管理者が一人もいなければ全員を管理者扱い（後方互換）"""
    any_admin = db.query(TeamMember).filter_by(team_id=team_id, is_admin=True).first()
    if any_admin is None:
        # 管理者未設定のチーム（旧データ）は全員が操作可能
        return True
    member = db.query(TeamMember).filter_by(team_id=team_id, user_id=user_id).first()
    return bool(member and member.is_admin)


def require_admin(db: Session, user_id: int, team_id: int) -> None:
    if not is_team_admin(db, user_id, team_id):
        raise HTTPException(status_code=403, detail="この操作は管理者のみ可能です")


def create_team(db: Session, data: TeamCreate, creator_user_id: int | None = None) -> Team:
    if db.query(Team).filter(Team.name == data.name).first():
        raise HTTPException(status_code=400, detail="同名のチームが既に存在します")
    team = Team(name=data.name, line_group_id=data.line_group_id)
    db.add(team)
    db.commit()
    db.refresh(team)
    if creator_user_id:
        db.add(TeamMember(team_id=team.id, user_id=creator_user_id, is_admin=True))
        db.commit()
    return team


def list_teams(db: Session) -> list[Team]:
    return db.query(Team).all()


def update_team(db: Session, team_id: int, data: TeamUpdate) -> Team:
    team = db.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="チームが見つかりません")
    if data.line_group_id is not None:
        team.line_group_id = data.line_group_id or None
    db.commit()
    db.refresh(team)
    return team


def rename_team(db: Session, team_id: int, data: TeamRename) -> Team:
    team = db.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="チームが見つかりません")
    if db.query(Team).filter(Team.name == data.name, Team.id != team_id).first():
        raise HTTPException(status_code=400, detail="同名のチームが既に存在します")
    team.name = data.name
    db.commit()
    db.refresh(team)
    return team


def delete_team(db: Session, team_id: int) -> None:
    team = db.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="チームが見つかりません")
    db.delete(team)
    db.commit()


def add_member(db: Session, team_id: int, user_id: int, is_admin: bool = False) -> None:
    if not db.get(Team, team_id):
        raise HTTPException(status_code=404, detail="チームが見つかりません")
    if not db.get(User, user_id):
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
    if db.query(TeamMember).filter_by(team_id=team_id, user_id=user_id).first():
        raise HTTPException(status_code=400, detail="既にメンバーです")
    db.add(TeamMember(team_id=team_id, user_id=user_id, is_admin=is_admin))
    db.commit()


def set_member_admin(db: Session, team_id: int, user_id: int, is_admin: bool) -> None:
    member = db.query(TeamMember).filter_by(team_id=team_id, user_id=user_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="メンバーが見つかりません")
    if not is_admin and member.is_admin:
        admin_count = db.query(TeamMember).filter_by(team_id=team_id, is_admin=True).count()
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="最後の管理者は降格できません")
    member.is_admin = is_admin
    db.commit()


def remove_member(db: Session, team_id: int, user_id: int) -> None:
    member = db.query(TeamMember).filter_by(team_id=team_id, user_id=user_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="メンバーが見つかりません")
    db.delete(member)
    db.commit()


def get_team_stats(db: Session, team_id: int) -> list[dict]:
    from datetime import datetime, timezone
    from app.models.attendance import Attendance, AttendanceStatus
    from app.models.event import Event

    team = db.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="チームが見つかりません")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    past_events = db.query(Event).filter(
        Event.team_id == team_id,
        Event.scheduled_at < now,
    ).all()
    total = len(past_events)
    event_ids = [e.id for e in past_events]

    result = []
    for m in team.members:
        if not event_ids:
            result.append({"id": m.user.id, "name": m.user.name, "total": 0, "attended": 0, "absent": 0, "pending": 0, "rate": None})
            continue
        attendances = db.query(Attendance).filter(
            Attendance.event_id.in_(event_ids),
            Attendance.user_id == m.user_id,
        ).all()
        att_map = {a.event_id: a.status for a in attendances}
        attended = sum(1 for eid in event_ids if att_map.get(eid) == AttendanceStatus.YES)
        absent   = sum(1 for eid in event_ids if att_map.get(eid) == AttendanceStatus.NO)
        pending  = total - attended - absent
        rate = round(attended / total * 100) if total > 0 else None
        result.append({"id": m.user.id, "name": m.user.name, "total": total, "attended": attended, "absent": absent, "pending": pending, "rate": rate})

    result.sort(key=lambda x: (x["rate"] is None, -(x["rate"] or 0)))
    return result


def list_members(db: Session, team_id: int) -> list[dict]:
    """メンバー一覧を is_admin フラグ付きで返す"""
    team = db.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="チームが見つかりません")
    return [
        {"id": m.user.id, "name": m.user.name, "line_id": m.user.line_id, "is_admin": m.is_admin}
        for m in team.members
    ]
