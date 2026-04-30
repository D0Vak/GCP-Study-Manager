from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.team import Team, TeamMember
from app.models.user import User
from app.schemas.team import TeamCreate


def create_team(db: Session, data: TeamCreate) -> Team:
    if db.query(Team).filter(Team.name == data.name).first():
        raise HTTPException(status_code=400, detail="同名のチームが既に存在します")
    team = Team(name=data.name, line_group_id=data.line_group_id)
    db.add(team)
    db.commit()
    db.refresh(team)
    return team


def list_teams(db: Session) -> list[Team]:
    return db.query(Team).all()


def add_member(db: Session, team_id: int, user_id: int) -> None:
    if not db.get(Team, team_id):
        raise HTTPException(status_code=404, detail="チームが見つかりません")
    if not db.get(User, user_id):
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
    if db.query(TeamMember).filter_by(team_id=team_id, user_id=user_id).first():
        raise HTTPException(status_code=400, detail="既にメンバーです")
    db.add(TeamMember(team_id=team_id, user_id=user_id))
    db.commit()


def list_members(db: Session, team_id: int) -> list[User]:
    team = db.get(Team, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="チームが見つかりません")
    return [m.user for m in team.members]
