from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import UserCreate


def create_user(db: Session, data: UserCreate) -> User:
    user = User(name=data.name, line_id=data.line_id)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def list_users(db: Session) -> list[User]:
    return db.query(User).all()


def delete_user(db: Session, user_id: int) -> None:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
    from app.models.attendance import Attendance
    from app.models.team import TeamMember
    db.query(TeamMember).filter(TeamMember.user_id == user_id).delete()
    db.query(Attendance).filter(Attendance.user_id == user_id).delete()
    db.delete(user)
    db.commit()
