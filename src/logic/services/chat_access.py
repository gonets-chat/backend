from collections.abc import Collection
from dataclasses import dataclass
from uuid import UUID

from enums import ChatRole, ChatType
from exc import (
    ChatAccessDeniedError,
    ChatNotFoundError,
    MessageNotFoundError,
    PermissionDeniedError,
)
from infrastructure.models import ChatMember, Message
from infrastructure.repositories.chat import ChatRepository
from infrastructure.repositories.chat_member import ChatMemberRepository
from infrastructure.repositories.message import MessageRepository


@dataclass(slots=True)
class ChatAccessService:
    chat_repository: ChatRepository
    chat_member_repository: ChatMemberRepository
    message_repository: MessageRepository

    async def require_chat_member(
        self,
        chat_id: UUID,
        user_id: UUID,
    ) -> ChatMember:
        member = await self.chat_member_repository.get_by_chat_and_user(
            chat_id=chat_id,
            user_id=user_id,
        )
        if member is None:
            raise ChatAccessDeniedError(user_id=user_id, chat_id=chat_id)

        return member

    async def require_chat_role(
        self,
        chat_id: UUID,
        user_id: UUID,
        allowed_roles: Collection[ChatRole],
    ) -> ChatMember:
        member = await self.require_chat_member(chat_id=chat_id, user_id=user_id)
        if member.role not in allowed_roles:
            raise ChatAccessDeniedError(user_id=user_id, chat_id=chat_id)

        return member

    async def require_message_author(
        self,
        message_id: UUID,
        user_id: UUID,
    ) -> Message:
        message = await self.message_repository.get_by_id(message_id)
        if message is None:
            raise MessageNotFoundError(message_id=message_id)

        await self.require_chat_member(chat_id=message.chat_id, user_id=user_id)
        if message.sender_id != user_id:
            raise PermissionDeniedError(user_id=user_id)

        return message

    async def require_message_delete_permission(
        self,
        message_id: UUID,
        user_id: UUID,
    ) -> Message:
        message = await self.message_repository.get_by_id(message_id)
        if message is None:
            raise MessageNotFoundError(message_id=message_id)

        if message.sender_id == user_id:
            await self.require_chat_member(
                chat_id=message.chat_id,
                user_id=user_id,
            )
            return message

        chat = await self.chat_repository.get_by_id(message.chat_id)
        if chat is None:
            raise ChatNotFoundError(chat_id=message.chat_id)

        if chat.type != ChatType.GROUP:
            raise PermissionDeniedError(user_id=user_id)

        await self.require_chat_role(
            chat_id=message.chat_id,
            user_id=user_id,
            allowed_roles={ChatRole.ADMIN, ChatRole.OWNER},
        )
        return message
