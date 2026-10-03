from fastapi import APIRouter, HTTPException, Request, Response

from api.dependencies import AuthServiceDep, UserServiceDep
from config import settings
from dto.user import UserCreate, UserLogin, UserResponse

auth_router = APIRouter(prefix="/auth", tags=["Auth"])


@auth_router.post(
    "/register", summary="Регистрация нового пользователя", status_code=201
)
async def register(user: UserCreate, user_service: UserServiceDep) -> UserResponse:
    return await user_service.register_user(user)


@auth_router.post("/login", summary="Авторизация пользователя")
async def login(
    credentials: UserLogin, auth_service: AuthServiceDep, response: Response
) -> dict[str, str]:
    """
    Авторизует пользователя и устанавливает JWT токен в HttpOnly cookie.
    """
    user = await auth_service.authenticate(credentials)

    tokens = await auth_service.authorization(user)

    response.set_cookie(
        key="access_token",
        value=tokens.access_token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        max_age=900,
        path="/",
    )

    response.set_cookie(
        key="refresh_token",
        value=tokens.refresh_token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        max_age=604800,
        path="/",
    )

    return {"message": "Успешный вход", "user_id": str(user.id)}


@auth_router.post("/logout", summary="Выйти из аккаунта")
async def logout(response: Response) -> None:
    """
    Выход пользователя - удаляет JWT токены из cookies.
    """
    response.delete_cookie(key="access_token", path="/")
    response.delete_cookie(key="refresh_token", path="/")


@auth_router.post("/refresh", summary="Обновить токены")
async def refresh_token(
    request: Request, auth_service: AuthServiceDep, response: Response
) -> dict[str, str]:
    """
    Обновляет access и refresh токены, используя refresh токен из cookies.
    """
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=400, detail="Refresh token is required")
    new_tokens = await auth_service.refresh_tokens(refresh_token)

    response.set_cookie(
        key="access_token",
        value=new_tokens.access_token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        max_age=900,
        path="/",
    )

    response.set_cookie(
        key="refresh_token",
        value=new_tokens.refresh_token,
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        max_age=604800,
        path="/",
    )

    return {"message": "Токены обновлены"}
