from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from dto.message import MessageResponse
from dto.user import UserListItem
from enums import ChatRole, ChatType


class ChatMemberDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    chat_id: UUID
    role: ChatRole
    user: UserListItem
    is_online: bool = False


class BaseDirectChat(BaseModel):
    type: ChatType = Field(default=ChatType.DIRECT)


class CreateDirectChat(BaseDirectChat):
    received_id: UUID


class UpdateDirectChat(BaseDirectChat):
    title: str


class ResponseDirectChat(BaseDirectChat):
    id: UUID
    title: str | None
    owner_id: UUID
    model_config = ConfigDict(from_attributes=True)
    members: list[ChatMemberDTO]
    last_message: MessageResponse | None = None


class BaseGroupChat(BaseModel):
    type: ChatType = Field(default=ChatType.GROUP)


class CreateGroupChat(BaseGroupChat):
    title: str
    member_ids: list[UUID]


class UpdateGroupChat(BaseModel):
    title: str


class ResponseGroupChat(BaseGroupChat):
    id: UUID
    title: str | None
    owner_id: UUID
    model_config = ConfigDict(from_attributes=True)
    members: list[ChatMemberDTO]
    last_message: MessageResponse | None = None
