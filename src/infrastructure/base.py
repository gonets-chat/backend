"""Базовый репозиторий: общие операции поверх сессии текущей транзакции."""

from abc import ABC
from uuid import UUID

from sqlalchemy import ColumnElement, Select, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, InstrumentedAttribute

from dto.pagination import CursorParams, Page


class BaseRepository[Model: DeclarativeBase](ABC):
    model: type[Model]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def exists(self, obj_id: UUID) -> bool:
        return await self.get_by_id(obj_id) is not None

    async def _create_with_object(self, obj: Model) -> Model:
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def _get_one_or_none(self, condition: ColumnElement[bool]) -> Model | None:
        result = await self.session.execute(select(self.model).where(condition))

        return result.scalar_one_or_none()

    async def get_by_id(self, obj_id: UUID) -> Model | None:
        return await self.session.get(self.model, obj_id)

    async def _paginate(
        self,
        stmt: Select[tuple[Model]],
        key: InstrumentedAttribute[UUID],
        params: CursorParams,
    ) -> Page[Model]:
        """Keyset-пагинация по уникальному возрастающему ключу (UUIDv7 id)."""
        if params.after is not None:
            stmt = stmt.where(key > params.after).order_by(key.asc())
        else:
            if params.before is not None:
                stmt = stmt.where(key < params.before)
            stmt = stmt.order_by(key.desc())

        # Берём на один элемент больше, чтобы узнать, есть ли следующая страница.
        rows = list(await self.session.scalars(stmt.limit(params.limit + 1)))
        items = rows[: params.limit]
        if params.after is None:
            items.reverse()

        return Page(items=items, has_more=len(rows) > params.limit)
