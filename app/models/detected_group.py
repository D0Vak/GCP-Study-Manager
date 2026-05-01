from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class DetectedGroup(Base):
    __tablename__ = "detected_groups"

    group_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    note: Mapped[str] = mapped_column(String(200), default="")
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
