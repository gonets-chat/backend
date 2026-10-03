from dataclasses import dataclass
from uuid import UUID

from asyncpg import NotNullViolationError, UniqueViolationError
from sqlalchemy.exc import IntegrityError

from dto.user import UserCreate, UserListItem, UserResponse
from exc import (
    EmailAlreadyExistsError,
    RequiredUserFieldError,
    UsernameAlreadyExistsError,
)
from infrastructure.repositories.user import UserRepository
from workers.taskiq.tasks import send_welcome_email


@dataclass(slots=True)
class UserService:
    repository: UserRepository

    async def get_user_by_id(self, user_id: UUID) -> UserResponse | None:
        user = await self.repository.get_by_id(user_id)
        if user is None:
            return None
        return UserResponse.model_validate(user)

    async def get_user_by_username(self, username: str) -> UserResponse | None:
        user = await self.repository.get_user_by_username(username)
        if user is None:
            return None
        return UserResponse.model_validate(user)

    async def register_user(self, user: UserCreate) -> UserResponse:
        try:
            user_model = await self.repository.create(user)
        except IntegrityError as exc:
            # SQLAlchemy оборачивает ошибку asyncpg: исходная лежит в __cause__.
            orig_error = exc.orig.__cause__ if exc.orig is not None else None

            if isinstance(orig_error, NotNullViolationError):
                raise RequiredUserFieldError from exc

            if isinstance(orig_error, UniqueViolationError):
                error_msg = str(orig_error)
                if "ix_users_email" in error_msg:
                    raise EmailAlreadyExistsError from exc
                if "ix_users_username" in error_msg:
                    raise UsernameAlreadyExistsError from exc

            raise
        await send_welcome_email.kiq(user_email=user.email, username=user.username)
        return UserResponse.model_validate(user_model)

    async def get_all_users(self, user_id: UUID) -> list[UserListItem]:
        users = await self.repository.get_all_users(user_id)
        return [UserListItem.model_validate(user) for user in users]
