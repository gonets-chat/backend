from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import joinedload, selectinload

from dto.chat import CreateGroupChat, UpdateGroupChat
from enums import ChatRole
from infrastructure.base import BaseRepository
from infrastructure.models import Chat, ChatMember


class GroupChatRepository(BaseRepository[Chat]):
    model = Chat

    async def create(self, obj: CreateGroupChat, owner_id: str) -> Chat:
        owner_uuid = UUID(owner_id)
        members = [ChatMember(user_id=owner_uuid, role=ChatRole.OWNER)] + [
            ChatMember(user_id=mid, role=ChatRole.MEMBER)
            for mid in obj.member_ids
            if mid != owner_uuid
        ]
        chat = Chat(
            type=obj.type,
            title=obj.title,
            owner_id=owner_uuid,
            members=members,
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

    async def update(self, obj_id: UUID, obj_in: UpdateGroupChat) -> Chat | None:
        chat = await self.session.get(self.model, obj_id)
        if chat is None:
            return None

        chat.title = obj_in.title

        await self.session.flush()
        return await self.get_by_id(obj_id)

    async def delete(self, obj_id: UUID) -> bool:
        chat = await self.session.get(self.model, obj_id)
        if chat is None:
            return False
        await self.session.delete(chat)
        await self.session.flush()
        return True

    async def get_all_chats_by_user_id(self, user_id: UUID) -> list[Chat] | None:
        stmt = (
            select(ChatMember)
            .where(ChatMember.user_id == user_id)
            .options(
                joinedload(ChatMember.chat)
                .selectinload(Chat.members)
                .joinedload(ChatMember.user),
            )
        )
        result = await self.session.execute(stmt)
        chat_members = result.scalars().all()
        if not chat_members:
            return []
        return [member.chat for member in chat_members]
