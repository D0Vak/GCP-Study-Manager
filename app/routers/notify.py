from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import CurrentUser
from app.database import get_db
from app.models.team import Team
from app.services import notification_service

router = APIRouter(prefix="/notify", tags=["notify"], dependencies=[CurrentUser])


class CustomMessage(BaseModel):
    team_id: int
    message: str


@router.post("")
def send_custom(data: CustomMessage, db: Session = Depends(get_db)):
    team = db.get(Team, data.team_id)
    if not team:
        raise HTTPException(status_code=404, detail="チームが見つかりません")
    notification_service.send_custom(db, team, data.message)
    return {"message": "送信しました"}
