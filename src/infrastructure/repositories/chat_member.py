from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.orm import aliased

from infrastructure.base import BaseRepository
from infrastructure.models import ChatMember


class ChatMemberRepository(BaseRepository[ChatMember]):
    model = ChatMember

    async def get_by_chat_and_user(
        self,
        chat_id: UUID,
        user_id: UUID,
    ) -> ChatMember | None:
        return await self._get_one_or_none(
            and_(
                self.model.chat_id == chat_id,
                self.model.user_id == user_id,
            )
        )

    async def get_member_ids(self, chat_id: UUID) -> set[UUID]:
        result = await self.session.execute(
            select(self.model.user_id).where(self.model.chat_id == chat_id)
        )
        return set(result.scalars())

    async def get_shared_chat_user_ids(self, user_id: UUID) -> set[UUID]:
        member = aliased(self.model)
        shared_member = aliased(self.model)

        stmt = (
            select(shared_member.user_id)
            .join(member, member.chat_id == shared_member.chat_id)
            .where(
                member.user_id == user_id,
                shared_member.user_id != user_id,
            )
            .distinct()
        )
        result = await self.session.execute(stmt)
        return set(result.scalars())
