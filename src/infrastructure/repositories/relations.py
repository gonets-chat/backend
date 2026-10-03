from uuid import UUID

from enums import RelationStatus
from infrastructure.base import BaseRepository
from infrastructure.models import UserRelation


class UserRelationRepository(BaseRepository[UserRelation]):
    model = UserRelation

    async def get_by_pair(
        self, user_id: UUID, target_user_id: UUID
    ) -> UserRelation | None:
        """Вспомогательный метод для поиска существующей связи между конкретной парой"""
        return await self._get_one_or_none(
            (self.model.user_id == user_id)
            & (self.model.target_user_id == target_user_id)
        )

    async def send_friend_request(
        self, user_id: UUID, target_user_id: UUID
    ) -> UserRelation:
        """
        Отправка заявки в друзья.
        Если связь уже существовала (например, была отклонена или отменена ранее),
        она обновится до PENDING, иначе создастся новая.
        """
        return await self._upsert_status(
            user_id=user_id,
            target_user_id=target_user_id,
            status=RelationStatus.PENDING,
        )

    async def accept_friend_request(self, relation_id: UUID) -> UserRelation | None:
        """Принятие заявки в друзья (перевод в статус FRIEND)"""
        return await self._set_status(relation_id, RelationStatus.FRIEND)

    async def reject_friend_request(self, relation_id: UUID) -> UserRelation | None:
        """Отклонение заявки в друзья (перевод в статус REJECTED)"""
        return await self._set_status(relation_id, RelationStatus.REJECTED)

    async def block_user(self, user_id: UUID, target_user_id: UUID) -> UserRelation:
        """
        Добавление пользователя в черный список.
        Если от инициатора (user_id) к цели (target_user_id) уже была какая-то связь,
        она перезаписывается на статус BLOCKED.
        """
        return await self._upsert_status(
            user_id=user_id,
            target_user_id=target_user_id,
            status=RelationStatus.BLOCKED,
        )

    async def _set_status(
        self, relation_id: UUID, status: RelationStatus
    ) -> UserRelation | None:
        relation = await self.get_by_id(relation_id)
        if not relation:
            return None

        relation.status = status
        await self.session.flush()
        await self.session.refresh(relation)
        return relation

    async def _upsert_status(
        self, user_id: UUID, target_user_id: UUID, status: RelationStatus
    ) -> UserRelation:
        relation = await self.get_by_pair(
            user_id=user_id, target_user_id=target_user_id
        )
        if relation:
            relation.status = status
            await self.session.flush()
            await self.session.refresh(relation)
            return relation

        return await self._create_with_object(
            obj=UserRelation(
                user_id=user_id,
                target_user_id=target_user_id,
                status=status,
            )
        )
