from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest

from dto.chat import CreateDirectChat
from enums import ChatRole, ChatType
from exc import DirectChatSelfError
from infrastructure.exceptions import UserNotFoundError
from infrastructure.protocol import PresenceProvider
from infrastructure.repositories.chat_member import ChatMemberRepository
from infrastructure.repositories.direct_chat import DirectChatRepository
from infrastructure.repositories.group_chat import GroupChatRepository
from infrastructure.repositories.message import MessageRepository
from infrastructure.repositories.user import UserRepository
from logic.services.chat import ChatService
from logic.services.chat_access import ChatAccessService


def make_direct_chat(owner_id: UUID, received_id: UUID) -> SimpleNamespace:
    chat_id = uuid4()

    def make_member(user_id: UUID, username: str) -> SimpleNamespace:
        return SimpleNamespace(
            id=uuid4(),
            user_id=user_id,
            chat_id=chat_id,
            role=ChatRole.MEMBER,
            user=SimpleNamespace(
                id=user_id,
                username=username,
                first_name="Test",
                second_name="User",
                avatar_url=None,
            ),
        )

    return SimpleNamespace(
        id=chat_id,
        type=ChatType.DIRECT,
        title=None,
        owner_id=owner_id,
        members=[
            make_member(owner_id, "owner"),
            make_member(received_id, "received"),
        ],
        messages=[],
    )


@pytest.fixture
def direct_chat_repository() -> AsyncMock:
    return AsyncMock(spec=DirectChatRepository)


@pytest.fixture
def user_repository() -> AsyncMock:
    return AsyncMock(spec=UserRepository)


@pytest.fixture
def chat_member_repository() -> AsyncMock:
    return AsyncMock(spec=ChatMemberRepository)


@pytest.fixture
def presence_provider() -> Mock:
    provider = Mock(spec=PresenceProvider)
    provider.is_online.return_value = False
    return provider


@pytest.fixture
def chat_service(
    direct_chat_repository: AsyncMock,
    chat_member_repository: AsyncMock,
    user_repository: AsyncMock,
    presence_provider: Mock,
) -> ChatService:
    message_repository = AsyncMock(spec=MessageRepository)
    message_repository.get_last_by_chat_ids.return_value = {}
    return ChatService(
        direct_chat_repository=direct_chat_repository,
        group_chat_repository=AsyncMock(spec=GroupChatRepository),
        chat_member_repository=chat_member_repository,
        message_repository=message_repository,
        user_repository=user_repository,
        access_service=AsyncMock(spec=ChatAccessService),
        presence_provider=presence_provider,
    )


@pytest.mark.asyncio
async def test_get_or_create_direct_chat_returns_existing_chat(
    chat_service: ChatService,
    direct_chat_repository: AsyncMock,
    user_repository: AsyncMock,
    presence_provider: Mock,
) -> None:
    owner_id = uuid4()
    received_id = uuid4()
    existing = make_direct_chat(owner_id, received_id)
    user_repository.exists.return_value = True
    direct_chat_repository.get_by_members.return_value = existing
    presence_provider.is_online.side_effect = lambda member_id: (
        member_id == received_id
    )

    result = await chat_service.get_or_create_direct_chat(
        CreateDirectChat(received_id=received_id),
        str(owner_id),
    )

    assert result.id == existing.id
    assert {
        member.user_id: member.is_online for member in result.members
    } == {
        owner_id: False,
        received_id: True,
    }
    direct_chat_repository.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_or_create_direct_chat_creates_missing_chat(
    chat_service: ChatService,
    direct_chat_repository: AsyncMock,
    user_repository: AsyncMock,
) -> None:
    owner_id = uuid4()
    received_id = uuid4()
    created = make_direct_chat(owner_id, received_id)
    user_repository.exists.return_value = True
    direct_chat_repository.get_by_members.return_value = None
    direct_chat_repository.create.return_value = created

    result = await chat_service.get_or_create_direct_chat(
        CreateDirectChat(received_id=received_id),
        str(owner_id),
    )

    assert result.id == created.id
    direct_chat_repository.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_or_create_direct_chat_rejects_self(
    chat_service: ChatService,
) -> None:
    user_id = uuid4()

    with pytest.raises(DirectChatSelfError):
        await chat_service.get_or_create_direct_chat(
            CreateDirectChat(received_id=user_id),
            str(user_id),
        )


@pytest.mark.asyncio
async def test_get_or_create_direct_chat_rejects_missing_user(
    chat_service: ChatService,
    user_repository: AsyncMock,
) -> None:
    owner_id = uuid4()
    received_id = uuid4()
    user_repository.exists.return_value = False

    with pytest.raises(UserNotFoundError):
        await chat_service.get_or_create_direct_chat(
            CreateDirectChat(received_id=received_id),
            str(owner_id),
        )


@pytest.mark.asyncio
async def test_get_shared_chat_user_ids_uses_member_repository(
    chat_service: ChatService,
    chat_member_repository: AsyncMock,
) -> None:
    user_id = uuid4()
    shared_user_ids = {uuid4(), uuid4()}
    chat_member_repository.get_shared_chat_user_ids.return_value = shared_user_ids

    result = await chat_service.get_shared_chat_user_ids(user_id)

    assert result == shared_user_ids
    chat_member_repository.get_shared_chat_user_ids.assert_awaited_once_with(user_id)
