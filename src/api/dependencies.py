from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from exc import AccessTokenNotFoundError
from factory import build_services, open_services
from infrastructure.database import get_write_session
from logic.services.auth import AuthService
from logic.services.chat import ChatService
from logic.services.message import MessageService
from logic.services.user import UserService
from tokens import AccessToken, verify_access_token
from types_alias import Services, ServicesFactory


async def get_session() -> AsyncGenerator[AsyncSession]:
    """Одна транзакция на HTTP-запрос: commit при успехе, rollback при ошибке."""
    async with get_write_session() as session:
        yield session


# scope="function" фиксирует транзакцию до отправки ответа клиенту.
SessionDep = Annotated[AsyncSession, Depends(get_session, scope="function")]


def get_services(session: SessionDep) -> Services:
    return build_services(session)


ServicesDep = Annotated[Services, Depends(get_services)]


def get_user_service(services: ServicesDep) -> UserService:
    return services.user


def get_auth_service(services: ServicesDep) -> AuthService:
    return services.auth


def get_chat_service(services: ServicesDep) -> ChatService:
    return services.chat


def get_message_service(services: ServicesDep) -> MessageService:
    return services.message


def get_services_factory() -> ServicesFactory:
    """Фабрика транзакций для долгоживущих соединений (WebSocket, фоновые задачи)."""
    return open_services


def verify_access_token_dep(request: Request) -> AccessToken:
    token = request.cookies.get("access_token")
    if not token:
        raise AccessTokenNotFoundError

    return verify_access_token(token)


VerifyAccessTokenDep = Annotated[AccessToken, Depends(verify_access_token_dep)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
MessageServiceDep = Annotated[MessageService, Depends(get_message_service)]
ServicesFactoryDep = Annotated[ServicesFactory, Depends(get_services_factory)]
