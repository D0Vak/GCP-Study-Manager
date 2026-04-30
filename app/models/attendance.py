import enum

from sqlalchemy import Enum, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AttendanceStatus(str, enum.Enum):
    YES = "yes"
    NO = "no"
    PENDING = "pending"


class Attendance(Base):
    __tablename__ = "attendances"
    __table_args__ = (UniqueConstraint("event_id", "user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    event_id: Mapped[int] = mapped_column(ForeignKey("events.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[AttendanceStatus] = mapped_column(Enum(AttendanceStatus), default=AttendanceStatus.PENDING)

    event: Mapped["Event"] = relationship(back_populates="attendances")
    user: Mapped["User"] = relationship(back_populates="attendances")
