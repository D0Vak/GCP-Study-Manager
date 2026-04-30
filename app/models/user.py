from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True, index=True)
    google_id: Mapped[str | None] = mapped_column(String(100), nullable=True, unique=True, index=True)
    line_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    team_memberships: Mapped[list["TeamMember"]] = relationship(back_populates="user")
    attendances: Mapped[list["Attendance"]] = relationship(back_populates="user")
