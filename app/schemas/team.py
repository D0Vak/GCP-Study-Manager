from pydantic import BaseModel

from app.schemas.user import UserResponse


class TeamCreate(BaseModel):
    name: str
    line_group_id: str | None = None


class TeamUpdate(BaseModel):
    line_group_id: str | None = None


class TeamRename(BaseModel):
    name: str


class TeamMemberAdd(BaseModel):
    user_id: int


class TeamMemberUpdate(BaseModel):
    is_admin: bool


class TeamMemberResponse(UserResponse):
    is_admin: bool = False


class TeamResponse(BaseModel):
    id: int
    name: str
    line_group_id: str | None

    model_config = {"from_attributes": True}


class TeamDetailResponse(TeamResponse):
    members: list[UserResponse] = []
