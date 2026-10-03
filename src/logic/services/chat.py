from dataclasses import dataclass
from uuid import UUID

from dto.chat import (
    CreateDirectChat,
    CreateGroupChat,
    ResponseDirectChat,
    ResponseGroupChat,
    UpdateGroupChat,
)
from dto.message import MessageResponse
from enums import ChatRole, ChatType
from exc import ChatNotFoundError, DirectChatSelfError
from infrastructure.exceptions import UserNotFoundError
from infrastructure.protocol import PresenceProvider
from infrastructure.repositories.chat_member import ChatMemberRepository
from infrastructure.repositories.direct_chat import DirectChatRepository
from infrastructure.repositories.group_chat import GroupChatRepository
from infrastructure.repositories.message import MessageRepository
from infrastructure.repositories.user import UserRepository
from logic.services.chat_access import ChatAccessService


@dataclass(slots=True)
class ChatService:
    direct_chat_repository: DirectChatRepository
    group_chat_repository: GroupChatRepository
    chat_member_repository: ChatMemberRepository
    message_repository: MessageRepository
    user_repository: UserRepository
    access_service: ChatAccessService
    presence_provider: PresenceProvider

    def _with_presence[ChatResponse: (ResponseDirectChat, ResponseGroupChat)](
        self, response: ChatResponse
    ) -> ChatResponse:
        members = [
            member.model_copy(
                update={
                    "is_online": self.presence_provider.is_online(member.user_id),
                }
            )
            for member in response.members
        ]
        return response.model_copy(update={"members": members})

    async def _with_last_messages[ChatT: (ResponseDirectChat, ResponseGroupChat)](
        self, responses: list[ChatT]
    ) -> list[ChatT]:
        last_messages = await self.message_repository.get_last_by_chat_ids(
            [response.id for response in responses]
        )
        return [
            response.model_copy(
                update={"last_message": MessageResponse.model_validate(message)}
            )
            if (message := last_messages.get(response.id)) is not None
            else response
            for response in responses
        ]

    async def _prepare[ChatResponse: (ResponseDirectChat, ResponseGroupChat)](
        self, response: ChatResponse
    ) -> ChatResponse:
        [prepared] = await self._with_last_messages([self._with_presence(response)])
        return prepared

    # --- Direct Chat ---

    async def get_or_create_direct_chat(
        self, chat: CreateDirectChat, owner_id: str
    ) -> ResponseDirectChat:
        owner_uuid = UUID(owner_id)
        if chat.received_id == owner_uuid:
            raise DirectChatSelfError(user_id=owner_uuid)

        if not await self.user_repository.exists(chat.received_id):
            raise UserNotFoundError(chat.received_id)

        await self.direct_chat_repository.lock_members_pair(
            user_id=owner_uuid,
            received_id=chat.received_id,
        )
        existing = await self.direct_chat_repository.get_by_members(
            user_id=owner_uuid,
            received_id=chat.received_id,
        )
        if existing is not None:
            return await self._prepare(ResponseDirectChat.model_validate(existing))

        created = await self.direct_chat_repository.create(obj=chat, owner_id=owner_id)
        response = ResponseDirectChat.model_validate(created)
        return self._with_presence(response)

    # --- Group Chat ---

    async def create_group_chat(
        self, chat: CreateGroupChat, owner_id: str
    ) -> ResponseGroupChat:
        created = await self.group_chat_repository.create(obj=chat, owner_id=owner_id)
        response = ResponseGroupChat.model_validate(created)
        return self._with_presence(response)

    async def update_group_chat(
        self,
        chat_id: UUID,
        obj_in: UpdateGroupChat,
        user_id: UUID,
    ) -> ResponseGroupChat:
        chat = await self.group_chat_repository.get_by_id(chat_id)
        if chat is None or chat.type != ChatType.GROUP:
            raise ChatNotFoundError(chat_id=chat_id)

        await self.access_service.require_chat_role(
            chat_id=chat_id,
            user_id=user_id,
            allowed_roles={ChatRole.ADMIN, ChatRole.OWNER},
        )
        updated = await self.group_chat_repository.update(obj_id=chat_id, obj_in=obj_in)
        if updated is None:
            raise ChatNotFoundError(chat_id=chat_id)

        return await self._prepare(ResponseGroupChat.model_validate(updated))

    async def delete_group_chat(self, chat_id: UUID, user_id: UUID) -> None:
        chat = await self.group_chat_repository.get_by_id(chat_id)
        if chat is None or chat.type != ChatType.GROUP:
            raise ChatNotFoundError(chat_id=chat_id)

        await self.access_service.require_chat_role(
            chat_id=chat_id,
            user_id=user_id,
            allowed_roles={ChatRole.OWNER},
        )
        deleted = await self.group_chat_repository.delete(obj_id=chat_id)
        if not deleted:
            raise ChatNotFoundError(chat_id=chat_id)

    async def get_chat(self, chat_id: UUID) -> ResponseGroupChat:
        chat = await self.group_chat_repository.get_by_id(chat_id)

        if not chat:
            raise ChatNotFoundError(chat_id=chat_id)

        return await self._prepare(ResponseGroupChat.model_validate(chat))

    async def get_all_chats(
        self, user_id: UUID
    ) -> list[ResponseGroupChat] | list[None]:
        group_chats = await self.group_chat_repository.get_all_chats_by_user_id(user_id)
        if not group_chats:
            return []
        return await self._with_last_messages(
            [
                self._with_presence(ResponseGroupChat.model_validate(chat))
                for chat in group_chats
            ]
        )

    async def get_member_ids(self, chat_id: UUID) -> set[UUID]:
        return await self.chat_member_repository.get_member_ids(chat_id)

    async def get_shared_chat_user_ids(self, user_id: UUID) -> set[UUID]:
        return await self.chat_member_repository.get_shared_chat_user_ids(user_id)
