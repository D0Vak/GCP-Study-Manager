from pydantic import BaseModel

from app.models.attendance import AttendanceStatus
from app.schemas.user import UserResponse


class AttendanceUpsert(BaseModel):
    user_id: int
    status: AttendanceStatus


class AttendanceRecord(BaseModel):
    user: UserResponse
    status: AttendanceStatus

    model_config = {"from_attributes": True}
