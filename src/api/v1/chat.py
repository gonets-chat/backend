from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query, status

from api.dependencies import (
    ChatServiceDep,
    MessageServiceDep,
    VerifyAccessTokenDep,
)
from dto.chat import (
    CreateDirectChat,
    CreateGroupChat,
    ResponseDirectChat,
    ResponseGroupChat,
    UpdateGroupChat,
)
from dto.message import MessageCreate, MessageResponse, MessageUpdateDTO
from dto.pagination import CursorParams, Page

chat_router = APIRouter(prefix="/chat", tags=["Chat"])


# --- Direct Chat ---


@chat_router.post(
    "/direct",
    response_model=ResponseDirectChat,
    status_code=status.HTTP_200_OK,
    summary="Получить или создать личный чат",
)
async def get_or_create_direct_chat(
    chat: CreateDirectChat,
    service: ChatServiceDep,
    token: VerifyAccessTokenDep,
) -> ResponseDirectChat:
    return await service.get_or_create_direct_chat(
        chat=chat,
        owner_id=token.payload.sub,
    )


# --- Group Chat ---


@chat_router.post(
    "/group",
    response_model=ResponseGroupChat,
    status_code=status.HTTP_201_CREATED,
    summary="Создать групповой чат",
)
async def create_group_chat(
    chat: CreateGroupChat,
    service: ChatServiceDep,
    token: VerifyAccessTokenDep,
) -> ResponseGroupChat:
    return await service.create_group_chat(chat=chat, owner_id=token.payload.sub)


@chat_router.patch(
    "/group/{chat_id}",
    response_model=ResponseGroupChat,
    summary="Обновить групповой чат",
)
async def update_group_chat(
    chat_id: UUID,
    obj_in: UpdateGroupChat,
    service: ChatServiceDep,
    token: VerifyAccessTokenDep,
) -> ResponseGroupChat:
    return await service.update_group_chat(
        chat_id=chat_id,
        obj_in=obj_in,
        user_id=UUID(token.payload.sub),
    )


@chat_router.delete(
    "/group/{chat_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить групповой чат",
)
async def delete_group_chat(
    chat_id: UUID,
    service: ChatServiceDep,
    token: VerifyAccessTokenDep,
) -> None:
    await service.delete_group_chat(
        chat_id=chat_id,
        user_id=UUID(token.payload.sub),
    )


@chat_router.post(
    "/{chat_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Отправить сообщение",
)
async def send_message(
    chat_id: UUID,
    obj: MessageCreate,
    service: MessageServiceDep,
    token: VerifyAccessTokenDep,
) -> MessageResponse:
    return await service.create_message_in_db(
        obj=obj.model_copy(update={"chat_id": chat_id}),
        sender_id=UUID(token.payload.sub),
    )


@chat_router.get(
    "/{chat_id}/messages",
    response_model=Page[MessageResponse],
    summary="Получить страницу сообщений чата",
)
async def get_chat_messages(
    chat_id: UUID,
    params: Annotated[CursorParams, Query()],
    service: MessageServiceDep,
    token: VerifyAccessTokenDep,
) -> Page[MessageResponse]:
    """Без курсора — последние сообщения; `before` — старше; `after` — новее."""
    return await service.get_chat_messages(
        chat_id=chat_id,
        user_id=UUID(token.payload.sub),
        params=params,
    )


@chat_router.patch(
    "/messages/{message_id}",
    response_model=MessageResponse,
    summary="Редактировать сообщение",
)
async def update_message(
    message_id: UUID,
    obj_in: MessageUpdateDTO,
    service: MessageServiceDep,
    token: VerifyAccessTokenDep,
) -> MessageResponse:
    return await service.update_message(
        message_id=message_id,
        obj_in=obj_in,
        user_id=UUID(token.payload.sub),
    )


@chat_router.delete(
    "/messages/{message_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удалить сообщение",
)
async def delete_message(
    message_id: UUID,
    service: MessageServiceDep,
    token: VerifyAccessTokenDep,
) -> None:
    await service.delete_message(
        message_id=message_id,
        user_id=UUID(token.payload.sub),
    )


@chat_router.get(
    "/all",
    response_model=list[ResponseGroupChat],
    summary="Получить все чаты пользователя",
)
async def get_all_chats(
    service: ChatServiceDep,
    token: VerifyAccessTokenDep,
) -> list[ResponseGroupChat] | list[None]:
    return await service.get_all_chats(user_id=UUID(token.payload.sub))
