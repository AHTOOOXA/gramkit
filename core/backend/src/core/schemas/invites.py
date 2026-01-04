from pydantic import BaseModel


class InviteTokens(BaseModel):
    user_token: str
    group_token: str


class InviteLink(BaseModel):
    link: str
