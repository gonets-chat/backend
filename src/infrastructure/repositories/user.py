from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select

from dto.user import UserCreate, UserUpdate
from infrastructure.base import BaseRepository
from infrastructure.exceptions import UserNotFoundError
from infrastructure.models import User
from utils import hash_password


class UserRepository(BaseRepository[User]):
    model = User

    async def create(self, obj: UserCreate) -> User:
        user = User(
            username=obj.username,
            email=obj.email,
            first_name=obj.first_name,
            second_name=obj.second_name,
            hashed_password=hash_password(obj.password),
            avatar_url=obj.avatar_url,
        )
        return await self._create_with_object(obj=user)

    async def update(self, obj_id: UUID, obj_in: UserUpdate) -> User:
        user = await self.get_by_id(obj_id)

        if not user:
            raise UserNotFoundError(user_id=obj_id)

        if obj_in.username:
            user.username = obj_in.username

        if obj_in.email:
            user.email = obj_in.email

        if obj_in.avatar_url:
            user.avatar_url = obj_in.avatar_url

        if obj_in.password:
            user.hashed_password = hash_password(obj_in.password)

        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def delete(self, obj_id: UUID) -> None:
        user = await self.get_by_id(obj_id)

        if not user:
            raise UserNotFoundError(user_id=obj_id)

        await self.session.delete(user)
        await self.session.flush()

    async def get_user_by_email(self, email: str) -> User | None:
        return await self._get_one_or_none(User.email == email)

    async def get_user_by_username(self, username: str) -> User | None:
        return await self._get_one_or_none(User.username == username)

    async def get_user_by_username_or_email(
        self,
        username: str | None = None,
        email: str | None = None,
    ) -> User | None:
        conditions = []

        if username:
            conditions.append(User.username == username)

        if email:
            conditions.append(User.email == email)

        if not conditions:
            return None

        return await self._get_one_or_none(*conditions)

    async def get_all_users(self, user_id: UUID) -> Sequence[User]:
        result = await self.session.execute(select(User).where(User.id != user_id))
        return result.scalars().all()
