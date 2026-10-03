from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from enums import ChatRole, ChatType, RelationStatus


class TimestampProtocol(Protocol):
    created_at: datetime
    updated_at: datetime


class UserProtocol(TimestampProtocol, Protocol):
    id: UUID
    username: str
    email: str
    hashed_password: str
    avatar_url: str | None

    memberships: list[ChatMemberProtocol]
    messages: list[MessageProtocol]
    sessions: list[UserSessionProtocol]

    def verify_password(self, plain_password: str) -> bool: ...


class ChatProtocol(TimestampProtocol, Protocol):
    id: UUID
    type: ChatType
    title: str | None
    owner_id: UUID | None

    # Связи
    members: list[ChatMemberProtocol]
    messages: list[MessageProtocol]


class ChatMemberProtocol(TimestampProtocol, Protocol):
    id: int
    user_id: UUID
    chat_id: UUID
    role: ChatRole

    # Связи
    user: UserProtocol
    chat: ChatProtocol


class MessageProtocol(TimestampProtocol, Protocol):
    id: UUID
    chat_id: UUID
    sender_id: UUID
    text: str
    attachments: dict | None
    is_read: bool

    # Связи
    chat: ChatProtocol
    sender: UserProtocol


class UserSessionProtocol(TimestampProtocol, Protocol):
    id: UUID
    user_id: UUID
    refresh_token: str
    ip_address: str | None
    user_agent: str | None
    is_blocked: bool
    expires_at: datetime

    # Связи
    user: UserProtocol


class UserRelationProtocol(TimestampProtocol, Protocol):
    id: int
    user_id: UUID
    target_user_id: UUID
    status: RelationStatus


class PresenceProvider(Protocol):
    def is_online(self, user_id: UUID) -> bool: ...
