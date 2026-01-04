from enum import StrEnum

from pydantic import BaseModel

from core.schemas.users import GroupSchema, UserSchema


class StartMode(StrEnum):
    DRAW = "draw"


class StartParamsRequest(BaseModel):
    invite_code: str | None = None
    referal_id: str | None = None
    mode: StartMode | None = None
    page: str | None = None
    timezone: str | None = None


class StartData(BaseModel):
    current_user: UserSchema
    inviter: GroupSchema | None = None
    mode: StartMode | None = None
