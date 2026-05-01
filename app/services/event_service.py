from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.event import Event, EventStatus
from app.models.team import Team
from app.schemas.event import EventCreate, EventUpdate


def create_event(db: Session, data: EventCreate) -> Event:
    if not db.get(Team, data.team_id):
        raise HTTPException(status_code=404, detail="チームが見つかりません")
    event = Event(
        team_id=data.team_id,
        title=data.title,
        scheduled_at=data.scheduled_at,
        status=EventStatus.SCHEDULED,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def list_events(db: Session, team_id: int | None = None) -> list[Event]:
    q = db.query(Event)
    if team_id is not None:
        q = q.filter(Event.team_id == team_id)
    return q.order_by(Event.scheduled_at).all()


def get_next_event(db: Session, team_id: int) -> Event | None:
    if not db.get(Team, team_id):
        raise HTTPException(status_code=404, detail="チームが見つかりません")
    return (
        db.query(Event)
        .filter(
            Event.team_id == team_id,
            Event.status == EventStatus.SCHEDULED,
            Event.scheduled_at >= datetime.now(),
        )
        .order_by(Event.scheduled_at)
        .first()
    )


def update_status(db: Session, event_id: int, status: EventStatus) -> Event:
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="イベントが見つかりません")
    event.status = status
    db.commit()
    db.refresh(event)
    return event


def update_event(db: Session, event_id: int, data: EventUpdate) -> Event:
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="イベントが見つかりません")
    if data.title is not None:
        event.title = data.title
    if data.scheduled_at is not None:
        event.scheduled_at = data.scheduled_at
    db.commit()
    db.refresh(event)
    return event


def delete_event(db: Session, event_id: int) -> None:
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="イベントが見つかりません")
    db.delete(event)
    db.commit()


def get_event_or_404(db: Session, event_id: int) -> Event:
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="イベントが見つかりません")
    return event
