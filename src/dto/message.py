"""Описывает данные сообщений и исходящие WebSocket-события сообщений."""

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import ConfigDict, Field, model_validator

from dto.base import DTOBase, WSServerEvent
from enums import WSEventType


class MessageBase(DTOBase):
    text: str = Field(min_length=1, max_length=4_000)


class MessageCreate(MessageBase):
    """Данные для создания сообщения."""

    chat_id: UUID


class MessageUpdateDTO(DTOBase):
    """Данные для изменения сообщения."""

    message_id: UUID
    text: str | None = Field(default=None, min_length=1, max_length=4_000)
    is_read: bool | None = None

    @model_validator(mode="after")
    def require_changes(self) -> Self:
        if self.text is None and self.is_read is None:
            msg = "At least one message field must be changed."
            raise ValueError(msg)

        return self


class MessageDeleteData(DTOBase):
    message_id: UUID


class MessageResponse(MessageBase):
    """Данные сохранённого сообщения."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    chat_id: UUID
    sender_id: UUID
    is_read: bool
    created_at: datetime
    updated_at: datetime | None = None


class MessageEventData(DTOBase):
    message: MessageResponse


class MessageDeletedData(DTOBase):
    message_id: UUID
    chat_id: UUID


class WSMessageCreatedEvent(WSServerEvent[MessageEventData]):
    type: WSEventType = Field(default=WSEventType.MESSAGE_CREATED)


class WSMessageUpdatedEvent(WSServerEvent[MessageEventData]):
    type: WSEventType = Field(default=WSEventType.MESSAGE_UPDATED, frozen=True)


class WSMessageDeletedEvent(WSServerEvent[MessageDeletedData]):
    type: WSEventType = WSEventType.MESSAGE_DELETED
