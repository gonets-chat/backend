from uuid import UUID

from fastapi import APIRouter, status

from api.dependencies import (
    UserServiceDep,
    VerifyAccessTokenDep,
)
from dto.user import UserCreate, UserListItem, UserResponse

user_router = APIRouter(prefix="/users", tags=["Users"])


@user_router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация нового пользователя",
)
async def register_user(
    user_data: UserCreate,
    user_service: UserServiceDep,
) -> UserResponse:
    """Зарегистрировать пользователя."""
    return await user_service.register_user(user_data)


@user_router.get(
    "",
    response_model=list[UserListItem],
    status_code=status.HTTP_200_OK,
    summary="Получить пользователей для поиска друзей",
)
async def get_all_users(
    user_service: UserServiceDep,
    token: VerifyAccessTokenDep,
) -> list[UserListItem]:
    """Вернуть только публичные данные пользователей без email и пароля."""
    return await user_service.get_all_users(UUID(token.payload.sub))
