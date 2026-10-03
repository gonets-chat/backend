from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from dto.user import UserLogin, UserResponse
from exc import InvalidCredentialsError, InvalidTokenError
from infrastructure.repositories.user import UserRepository
from tokens import (
    JwtTokens,
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
)


@dataclass(slots=True)
class AuthService:
    repository: UserRepository

    async def authorization(self, user: UserResponse) -> JwtTokens:
        access_token = create_access_token(exp=timedelta(minutes=15), sub=user.id)
        refresh_token = create_refresh_token(exp=timedelta(days=7), sub=user.id)
        return JwtTokens(access_token=access_token, refresh_token=refresh_token)

    async def authenticate(self, credentials: UserLogin) -> UserResponse:
        user = await self.repository.get_user_by_username_or_email(
            username=credentials.username, email=credentials.email
        )
        if not user or not user.verify_password(credentials.password):
            raise InvalidCredentialsError
        return UserResponse.model_validate(user)

    async def refresh_tokens(self, refresh_token: str) -> JwtTokens:
        refresh_token_data = verify_refresh_token(refresh_token)
        user_id = refresh_token_data.payload.sub
        user = await self.repository.get_by_id(UUID(user_id))
        if not user:
            raise InvalidTokenError

        new_access_token = create_access_token(exp=timedelta(minutes=15), sub=user.id)
        new_refresh_token = create_refresh_token(exp=timedelta(days=7), sub=user.id)

        return JwtTokens(access_token=new_access_token, refresh_token=new_refresh_token)
