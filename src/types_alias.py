from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar
from uuid import UUID

if TYPE_CHECKING:
    from logic.services.auth import AuthService
    from logic.services.chat import ChatService
    from logic.services.message import MessageService
    from logic.services.user import UserService

type Seconds = int
type UserID = UUID


class SingletonMeta(type):
    _instances: ClassVar[dict[type, object]] = {}

    def __call__(cls, *args: object, **kwargs: object):  # noqa: ANN204
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)

        return cls._instances[cls]


@dataclass(frozen=True, slots=True)
class Services:
    """Сервисы, работающие внутри одной транзакции базы данных."""

    user: UserService
    auth: AuthService
    chat: ChatService
    message: MessageService


type ServicesFactory = Callable[[], AbstractAsyncContextManager[Services]]
"""Открывает транзакцию и отдаёт сервисы, работающие внутри неё."""
