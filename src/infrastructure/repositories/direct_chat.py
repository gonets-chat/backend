from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from dto.chat import CreateDirectChat
from enums import ChatRole, ChatType
from infrastructure.base import BaseRepository
from infrastructure.models import Chat, ChatMember


class DirectChatRepository(BaseRepository[Chat]):
    model = Chat

    async def create(self, obj: CreateDirectChat, owner_id: str) -> Chat:
        owner_uuid = UUID(owner_id)
        members = (obj.received_id, owner_uuid)
        chat = Chat(
            type=obj.type,
            owner_id=owner_uuid,
            members=[
                ChatMember(user_id=user_id, role=ChatRole.MEMBER) for user_id in members
            ],
        )
        created = await self._create_with_object(obj=chat)
        return await self.get_by_id(created.id) or created

    async def get_by_id(self, obj_id: UUID) -> Chat | None:
        stmt = (
            select(self.model)
            .where(self.model.id == obj_id)
            .options(selectinload(self.model.members).joinedload(ChatMember.user))
            .execution_options(populate_existing=True)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def lock_members_pair(self, user_id: UUID, received_id: UUID) -> None:
        """Сериализует создание личного чата для пары до конца транзакции."""
        low, high = sorted((user_id, received_id))
        await self.session.execute(
            select(
                func.pg_advisory_xact_lock(
                    func.hashtextextended(f"direct_chat:{low}:{high}", 0)
                )
            )
        )

    async def get_by_members(
        self,
        user_id: UUID,
        received_id: UUID,
    ) -> Chat | None:
        user_chats = select(ChatMember.chat_id).where(ChatMember.user_id == user_id)
        received_chats = select(ChatMember.chat_id).where(
            ChatMember.user_id == received_id
        )
        stmt = (
            select(self.model)
            .where(
                self.model.type == ChatType.DIRECT,
                self.model.id.in_(user_chats),
                self.model.id.in_(received_chats),
            )
            .options(selectinload(self.model.members).joinedload(ChatMember.user))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
