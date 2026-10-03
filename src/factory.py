"""Собирает репозитории и сервисы приложения поверх одной транзакции базы данных."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.database import get_write_session
from infrastructure.repositories.chat import ChatRepository
from infrastructure.repositories.chat_member import ChatMemberRepository
from infrastructure.repositories.direct_chat import DirectChatRepository
from infrastructure.repositories.group_chat import GroupChatRepository
from infrastructure.repositories.message import MessageRepository
from infrastructure.repositories.user import UserRepository
from logic.services.auth import AuthService
from logic.services.chat import ChatService
from logic.services.chat_access import ChatAccessService
from logic.services.message import MessageService
from logic.services.user import UserService
from socket_app.connection_manager import connection_manager
from types_alias import Services


def build_services(session: AsyncSession) -> Services:
    user_repository = UserRepository(session)
    chat_member_repository = ChatMemberRepository(session)
    message_repository = MessageRepository(session)
    access_service = ChatAccessService(
        chat_repository=ChatRepository(session),
        chat_member_repository=chat_member_repository,
        message_repository=message_repository,
    )

    return Services(
        user=UserService(user_repository),
        auth=AuthService(user_repository),
        chat=ChatService(
            direct_chat_repository=DirectChatRepository(session),
            group_chat_repository=GroupChatRepository(session),
            chat_member_repository=chat_member_repository,
            message_repository=message_repository,
            user_repository=user_repository,
            access_service=access_service,
            presence_provider=connection_manager,
        ),
        message=MessageService(
            message_repository=message_repository,
            access_service=access_service,
        ),
    )


@asynccontextmanager
async def open_services() -> AsyncGenerator[Services]:
    """Одна транзакция: commit при успехе, rollback при ошибке."""
    async with get_write_session() as session:
        yield build_services(session)
