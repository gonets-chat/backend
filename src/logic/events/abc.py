"""Базовый контракт обработчиков WebSocket-команд."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID

from pydantic import BaseModel

from types_alias import Services


@dataclass(frozen=True, slots=True)
class Delivery:
    """Событие, которое отправляется получателям после фиксации транзакции."""

    recipient_ids: set[UUID]
    payload: str


class BaseEvent[DataT: BaseModel](ABC):
    @abstractmethod
    async def execute(
        self,
        services: Services,
        sender_id: UUID,
        data: DataT,
    ) -> Delivery: ...
