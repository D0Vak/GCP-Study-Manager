from pydantic import BaseModel


class UserCreate(BaseModel):
    name: str
    line_id: str | None = None


class UserResponse(BaseModel):
    id: int
    name: str
    line_id: str | None

    model_config = {"from_attributes": True}
