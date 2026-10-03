from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from enums import ChatRole, ChatType
from exc import (
    ChatAccessDeniedError,
    MessageNotFoundError,
    PermissionDeniedError,
)
from infrastructure.models import Chat, ChatMember, Message
from infrastructure.repositories.chat import ChatRepository
from infrastructure.repositories.chat_member import ChatMemberRepository
from infrastructure.repositories.message import MessageRepository
from logic.services.chat_access import ChatAccessService


@pytest.fixture
def chat_repository() -> AsyncMock:
    return AsyncMock(spec=ChatRepository)


@pytest.fixture
def chat_member_repository() -> AsyncMock:
    return AsyncMock(spec=ChatMemberRepository)


@pytest.fixture
def message_repository() -> AsyncMock:
    return AsyncMock(spec=MessageRepository)


@pytest.fixture
def access_service(
    chat_repository: AsyncMock,
    chat_member_repository: AsyncMock,
    message_repository: AsyncMock,
) -> ChatAccessService:
    return ChatAccessService(
        chat_repository=chat_repository,
        chat_member_repository=chat_member_repository,
        message_repository=message_repository,
    )


@pytest.mark.asyncio
async def test_require_chat_member_returns_member(
    access_service: ChatAccessService,
    chat_member_repository: AsyncMock,
) -> None:
    chat_id = uuid4()
    user_id = uuid4()
    member = ChatMember(
        chat_id=chat_id,
        user_id=user_id,
        role=ChatRole.MEMBER,
    )
    chat_member_repository.get_by_chat_and_user.return_value = member

    result = await access_service.require_chat_member(chat_id, user_id)

    assert result is member


@pytest.mark.asyncio
async def test_require_chat_member_rejects_non_member(
    access_service: ChatAccessService,
    chat_member_repository: AsyncMock,
) -> None:
    chat_id = uuid4()
    user_id = uuid4()
    chat_member_repository.get_by_chat_and_user.return_value = None

    with pytest.raises(ChatAccessDeniedError):
        await access_service.require_chat_member(chat_id, user_id)


@pytest.mark.asyncio
async def test_require_chat_role_accepts_allowed_role(
    access_service: ChatAccessService,
    chat_member_repository: AsyncMock,
) -> None:
    chat_id = uuid4()
    user_id = uuid4()
    member = ChatMember(
        chat_id=chat_id,
        user_id=user_id,
        role=ChatRole.ADMIN,
    )
    chat_member_repository.get_by_chat_and_user.return_value = member

    result = await access_service.require_chat_role(
        chat_id,
        user_id,
        {ChatRole.ADMIN, ChatRole.OWNER},
    )

    assert result is member


@pytest.mark.asyncio
async def test_require_chat_role_rejects_disallowed_role(
    access_service: ChatAccessService,
    chat_member_repository: AsyncMock,
) -> None:
    chat_id = uuid4()
    user_id = uuid4()
    chat_member_repository.get_by_chat_and_user.return_value = ChatMember(
        chat_id=chat_id,
        user_id=user_id,
        role=ChatRole.MEMBER,
    )

    with pytest.raises(ChatAccessDeniedError):
        await access_service.require_chat_role(
            chat_id,
            user_id,
            {ChatRole.ADMIN, ChatRole.OWNER},
        )


@pytest.mark.asyncio
async def test_require_message_author_returns_authored_message(
    access_service: ChatAccessService,
    chat_member_repository: AsyncMock,
    message_repository: AsyncMock,
) -> None:
    chat_id = uuid4()
    user_id = uuid4()
    message = Message(
        id=uuid4(),
        chat_id=chat_id,
        sender_id=user_id,
        text="message",
    )
    message_repository.get_by_id.return_value = message
    chat_member_repository.get_by_chat_and_user.return_value = ChatMember(
        chat_id=chat_id,
        user_id=user_id,
        role=ChatRole.MEMBER,
    )

    result = await access_service.require_message_author(message.id, user_id)

    assert result is message


@pytest.mark.asyncio
async def test_require_message_author_rejects_other_user(
    access_service: ChatAccessService,
    chat_member_repository: AsyncMock,
    message_repository: AsyncMock,
) -> None:
    chat_id = uuid4()
    user_id = uuid4()
    message = Message(
        id=uuid4(),
        chat_id=chat_id,
        sender_id=uuid4(),
        text="message",
    )
    message_repository.get_by_id.return_value = message
    chat_member_repository.get_by_chat_and_user.return_value = ChatMember(
        chat_id=chat_id,
        user_id=user_id,
        role=ChatRole.MEMBER,
    )

    with pytest.raises(PermissionDeniedError):
        await access_service.require_message_author(message.id, user_id)


@pytest.mark.asyncio
async def test_require_message_author_rejects_missing_message(
    access_service: ChatAccessService,
    message_repository: AsyncMock,
) -> None:
    message_id = uuid4()
    message_repository.get_by_id.return_value = None

    with pytest.raises(MessageNotFoundError):
        await access_service.require_message_author(message_id, uuid4())


@pytest.mark.asyncio
async def test_require_message_delete_permission_allows_author(
    access_service: ChatAccessService,
    chat_member_repository: AsyncMock,
    message_repository: AsyncMock,
) -> None:
    chat_id = uuid4()
    user_id = uuid4()
    message = Message(
        id=uuid4(),
        chat_id=chat_id,
        sender_id=user_id,
        text="message",
    )
    message_repository.get_by_id.return_value = message
    chat_member_repository.get_by_chat_and_user.return_value = ChatMember(
        chat_id=chat_id,
        user_id=user_id,
        role=ChatRole.MEMBER,
    )

    result = await access_service.require_message_delete_permission(
        message.id,
        user_id,
    )

    assert result is message


@pytest.mark.parametrize("role", [ChatRole.ADMIN, ChatRole.OWNER])
@pytest.mark.asyncio
async def test_require_message_delete_permission_allows_group_moderator(
    access_service: ChatAccessService,
    chat_repository: AsyncMock,
    chat_member_repository: AsyncMock,
    message_repository: AsyncMock,
    role: ChatRole,
) -> None:
    chat_id = uuid4()
    user_id = uuid4()
    message = Message(
        id=uuid4(),
        chat_id=chat_id,
        sender_id=uuid4(),
        text="message",
    )
    message_repository.get_by_id.return_value = message
    chat_member_repository.get_by_chat_and_user.return_value = ChatMember(
        chat_id=chat_id,
        user_id=user_id,
        role=role,
    )
    chat_repository.get_by_id.return_value = Chat(
        id=chat_id,
        type=ChatType.GROUP,
        owner_id=uuid4(),
    )

    result = await access_service.require_message_delete_permission(
        message.id,
        user_id,
    )

    assert result is message


@pytest.mark.asyncio
async def test_require_message_delete_permission_rejects_group_member(
    access_service: ChatAccessService,
    chat_repository: AsyncMock,
    chat_member_repository: AsyncMock,
    message_repository: AsyncMock,
) -> None:
    chat_id = uuid4()
    user_id = uuid4()
    message = Message(
        id=uuid4(),
        chat_id=chat_id,
        sender_id=uuid4(),
        text="message",
    )
    message_repository.get_by_id.return_value = message
    chat_member_repository.get_by_chat_and_user.return_value = ChatMember(
        chat_id=chat_id,
        user_id=user_id,
        role=ChatRole.MEMBER,
    )
    chat_repository.get_by_id.return_value = Chat(
        id=chat_id,
        type=ChatType.GROUP,
        owner_id=uuid4(),
    )

    with pytest.raises(PermissionDeniedError):
        await access_service.require_message_delete_permission(
            message.id,
            user_id,
        )


@pytest.mark.asyncio
async def test_require_message_delete_permission_rejects_direct_chat_admin(
    access_service: ChatAccessService,
    chat_repository: AsyncMock,
    chat_member_repository: AsyncMock,
    message_repository: AsyncMock,
) -> None:
    chat_id = uuid4()
    user_id = uuid4()
    message = Message(
        id=uuid4(),
        chat_id=chat_id,
        sender_id=uuid4(),
        text="message",
    )
    message_repository.get_by_id.return_value = message
    chat_member_repository.get_by_chat_and_user.return_value = ChatMember(
        chat_id=chat_id,
        user_id=user_id,
        role=ChatRole.ADMIN,
    )
    chat_repository.get_by_id.return_value = Chat(
        id=chat_id,
        type=ChatType.DIRECT,
        owner_id=uuid4(),
    )

    with pytest.raises(PermissionDeniedError):
        await access_service.require_message_delete_permission(
            message.id,
            user_id,
        )
