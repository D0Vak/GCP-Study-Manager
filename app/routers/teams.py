from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser, get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.team import TeamCreate, TeamMemberAdd, TeamMemberResponse, TeamMemberUpdate, TeamRename, TeamResponse, TeamUpdate
from app.services import team_service

router = APIRouter(prefix="/teams", tags=["teams"], dependencies=[CurrentUser])


@router.post("", response_model=TeamResponse, status_code=201)
def create_team(
    data: TeamCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return team_service.create_team(db, data, creator_user_id=current_user.id)


@router.get("", response_model=list[TeamResponse])
def list_teams(db: Session = Depends(get_db)):
    return team_service.list_teams(db)


@router.patch("/{team_id}", response_model=TeamResponse)
def update_team(team_id: int, data: TeamUpdate, db: Session = Depends(get_db)):
    return team_service.update_team(db, team_id, data)


@router.patch("/{team_id}/rename", response_model=TeamResponse)
def rename_team(team_id: int, data: TeamRename, db: Session = Depends(get_db)):
    return team_service.rename_team(db, team_id, data)


@router.delete("/{team_id}", status_code=204)
def delete_team(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    team_service.require_admin(db, current_user.id, team_id)
    team_service.delete_team(db, team_id)


@router.post("/{team_id}/members", status_code=201)
def add_member(team_id: int, data: TeamMemberAdd, db: Session = Depends(get_db)):
    team_service.add_member(db, team_id, data.user_id)
    return {"message": "メンバーを追加しました"}


@router.patch("/{team_id}/members/{user_id}")
def update_member(
    team_id: int,
    user_id: int,
    data: TeamMemberUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    team_service.require_admin(db, current_user.id, team_id)
    team_service.set_member_admin(db, team_id, user_id, data.is_admin)
    return {"message": "更新しました"}


@router.delete("/{team_id}/members/{user_id}", status_code=204)
def remove_member(
    team_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    team_service.require_admin(db, current_user.id, team_id)
    team_service.remove_member(db, team_id, user_id)


@router.get("/{team_id}/members", response_model=list[TeamMemberResponse])
def list_members(team_id: int, db: Session = Depends(get_db)):
    return team_service.list_members(db, team_id)


@router.get("/{team_id}/stats")
def get_stats(team_id: int, db: Session = Depends(get_db)):
    return team_service.get_team_stats(db, team_id)
