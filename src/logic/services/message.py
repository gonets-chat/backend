from dataclasses import dataclass
from uuid import UUID

from dto.message import MessageCreate, MessageResponse, MessageUpdateDTO
from dto.pagination import CursorParams, Page
from exc import MessageNotFoundError
from infrastructure.repositories.message import MessageRepository
from logic.services.chat_access import ChatAccessService


@dataclass(slots=True)
class MessageService:
    message_repository: MessageRepository
    access_service: ChatAccessService

    async def create_message_in_db(
        self, obj: MessageCreate, sender_id: UUID
    ) -> MessageResponse:
        await self.access_service.require_chat_member(
            chat_id=obj.chat_id,
            user_id=sender_id,
        )
        created = await self.message_repository.create(obj=obj, sender_id=sender_id)
        return MessageResponse.model_validate(created)

    async def get_chat_messages(
        self,
        chat_id: UUID,
        user_id: UUID,
        params: CursorParams,
    ) -> Page[MessageResponse]:
        await self.access_service.require_chat_member(
            chat_id=chat_id,
            user_id=user_id,
        )
        page = await self.message_repository.get_page(chat_id=chat_id, params=params)
        return page.map(MessageResponse.model_validate)

    async def update_message(
        self,
        message_id: UUID,
        obj_in: MessageUpdateDTO,
        user_id: UUID,
    ) -> MessageResponse:
        await self.access_service.require_message_author(
            message_id=message_id,
            user_id=user_id,
        )
        normalized_obj = obj_in.model_copy(update={"message_id": message_id})
        updated = await self.message_repository.update(obj_in=normalized_obj)
        if updated is None:
            raise MessageNotFoundError(message_id=message_id)
        return MessageResponse.model_validate(updated)

    async def delete_message(
        self,
        message_id: UUID,
        user_id: UUID,
    ) -> MessageResponse:
        message = await self.access_service.require_message_delete_permission(
            message_id=message_id,
            user_id=user_id,
        )
        response = MessageResponse.model_validate(message)
        deleted = await self.message_repository.delete(obj_id=message_id)
        if not deleted:
            raise MessageNotFoundError(message_id=message_id)
        return response
