from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import UserCreate, UserLineIdUpdate


def create_user(db: Session, data: UserCreate) -> User:
    user = User(name=data.name, line_id=data.line_id)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def list_users(db: Session) -> list[User]:
    return db.query(User).all()


def update_line_id(db: Session, user_id: int, data: UserLineIdUpdate) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="ユーザーが見つかりません")
    # 別ユーザーがすでにこのLINE IDを持っている場合はエラー
    if data.line_id:
        conflict = db.query(User).filter(User.line_id == data.line_id, User.id != user_id).first()
        if conflict:
            raise HTTPException(status_code=409, detail=f"このLINE IDは既に「{conflict.name}」に設定されています")
    user.line_id = data.line_id
    db.commit()
    db.refresh(user)
    return user


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
