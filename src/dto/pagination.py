"""Курсорная пагинация: параметры запроса и страница результата.

Курсор — id крайнего элемента, который клиент уже видел. UUIDv7 растут
со временем, поэтому сортировка по id совпадает с сортировкой по времени.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Self
from uuid import UUID

from pydantic import Field, model_validator

from dto.base import DTOBase


class CursorParams(DTOBase):
    """Без курсора — последние `limit` элементов.

    `before` — элементы старше курсора (листаем историю вверх).
    `after` — элементы новее курсора (досинхронизация после переподключения).
    """

    limit: int = Field(default=50, ge=1, le=100)
    before: UUID | None = None
    after: UUID | None = None

    @model_validator(mode="after")
    def require_single_direction(self) -> Self:
        if self.before is not None and self.after is not None:
            msg = "Use either 'before' or 'after', not both."
            raise ValueError(msg)

        return self


@dataclass(frozen=True, slots=True)
class Page[ItemT]:
    """Элементы всегда в хронологическом порядке: от старых к новым.

    Курсор следующего запроса: `items[0].id` для `before`,
    `items[-1].id` для `after`. `has_more` — есть ли элементы дальше.
    """

    items: list[ItemT]
    has_more: bool

    def map[NewItemT](self, convert: Callable[[ItemT], NewItemT]) -> Page[NewItemT]:
        return Page(
            items=[convert(item) for item in self.items], has_more=self.has_more
        )
