from datetime import datetime

from pydantic import BaseModel

from app.models.event import EventStatus


class EventCreate(BaseModel):
    team_id: int
    title: str
    scheduled_at: datetime


class EventUpdate(BaseModel):
    title: str | None = None
    scheduled_at: datetime | None = None


class EventStatusUpdate(BaseModel):
    status: EventStatus


class EventResponse(BaseModel):
    id: int
    team_id: int
    title: str
    scheduled_at: datetime
    status: EventStatus

    model_config = {"from_attributes": True}
