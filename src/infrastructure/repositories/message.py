from collections.abc import Collection
from uuid import UUID

from sqlalchemy import select

from dto.message import MessageCreate, MessageUpdateDTO
from dto.pagination import CursorParams, Page
from infrastructure.base import BaseRepository
from infrastructure.models import Message


class MessageRepository(BaseRepository[Message]):
    model = Message

    async def create(self, obj: MessageCreate, sender_id: UUID) -> Message:
        message = Message(
            chat_id=obj.chat_id,
            sender_id=sender_id,
            text=obj.text,
        )
        return await self._create_with_object(obj=message)

    async def get_page(self, chat_id: UUID, params: CursorParams) -> Page[Message]:
        stmt = select(self.model).where(self.model.chat_id == chat_id)
        return await self._paginate(stmt, self.model.id, params)

    async def get_last_by_chat_ids(
        self, chat_ids: Collection[UUID]
    ) -> dict[UUID, Message]:
        """Последнее сообщение каждого чата одним запросом (DISTINCT ON)."""
        if not chat_ids:
            return {}

        stmt = (
            select(self.model)
            .where(self.model.chat_id.in_(chat_ids))
            .order_by(self.model.chat_id, self.model.id.desc())
            .distinct(self.model.chat_id)
        )
        messages = await self.session.scalars(stmt)
        return {message.chat_id: message for message in messages}

    async def update(self, obj_in: MessageUpdateDTO) -> Message | None:
        message = await self.session.get(self.model, obj_in.message_id)
        if message is None:
            return None

        message.text = obj_in.text or message.text
        message.is_read = obj_in.is_read or message.is_read

        await self.session.flush()
        await self.session.refresh(message)
        return message

    async def delete(self, obj_id: UUID) -> bool:
        message = await self.session.get(self.model, obj_id)
        if message is None:
            return False
        await self.session.delete(message)
        await self.session.flush()
        return True

    async def mark_as_read(self, obj_id: UUID) -> Message | None:
        return await self.update(
            obj_in=MessageUpdateDTO(message_id=obj_id, is_read=True),
        )
