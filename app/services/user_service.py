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
