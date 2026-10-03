"""Обрабатывает команды создания, изменения и удаления сообщений."""

from uuid import UUID

from dto.message import (
    MessageCreate,
    MessageDeleteData,
    MessageDeletedData,
    MessageEventData,
    MessageUpdateDTO,
    WSMessageCreatedEvent,
    WSMessageDeletedEvent,
    WSMessageUpdatedEvent,
)
from logic.events.abc import BaseEvent, Delivery
from types_alias import Services


class MessageSend(BaseEvent[MessageCreate]):
    async def execute(
        self,
        services: Services,
        sender_id: UUID,
        data: MessageCreate,
    ) -> Delivery:
        message = await services.message.create_message_in_db(
            obj=data,
            sender_id=sender_id,
        )
        return Delivery(
            recipient_ids=await services.chat.get_member_ids(message.chat_id),
            payload=WSMessageCreatedEvent(
                data=MessageEventData(message=message),
            ).model_dump_json(),
        )


class MessageUpdate(BaseEvent[MessageUpdateDTO]):
    async def execute(
        self,
        services: Services,
        sender_id: UUID,
        data: MessageUpdateDTO,
    ) -> Delivery:
        message = await services.message.update_message(
            message_id=data.message_id,
            obj_in=data,
            user_id=sender_id,
        )
        return Delivery(
            recipient_ids=await services.chat.get_member_ids(message.chat_id),
            payload=WSMessageUpdatedEvent(
                data=MessageEventData(message=message),
            ).model_dump_json(),
        )


class MessageDelete(BaseEvent[MessageDeleteData]):
    async def execute(
        self,
        services: Services,
        sender_id: UUID,
        data: MessageDeleteData,
    ) -> Delivery:
        message = await services.message.delete_message(
            message_id=data.message_id,
            user_id=sender_id,
        )
        return Delivery(
            recipient_ids=await services.chat.get_member_ids(message.chat_id),
            payload=WSMessageDeletedEvent(
                data=MessageDeletedData(
                    message_id=message.id,
                    chat_id=message.chat_id,
                ),
            ).model_dump_json(),
        )
