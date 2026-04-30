import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class EventStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    DONE = "done"


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[EventStatus] = mapped_column(Enum(EventStatus), default=EventStatus.SCHEDULED)

    team: Mapped["Team"] = relationship(back_populates="events")
    attendances: Mapped[list["Attendance"]] = relationship(back_populates="event", cascade="all, delete-orphan")
