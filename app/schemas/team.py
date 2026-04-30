from pydantic import BaseModel

from app.schemas.user import UserResponse


class TeamCreate(BaseModel):
    name: str
    line_group_id: str | None = None


class TeamMemberAdd(BaseModel):
    user_id: int


class TeamResponse(BaseModel):
    id: int
    name: str
    line_group_id: str | None

    model_config = {"from_attributes": True}


class TeamDetailResponse(TeamResponse):
    members: list[UserResponse] = []
