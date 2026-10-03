from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from exc import LoginMethodAmbiguousError, LoginMethodRequiredError


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    first_name: str = Field(..., min_length=1, max_length=50)
    second_name: str = Field(..., min_length=1, max_length=50)
    avatar_url: str | None = None


class UserLogin(BaseModel):
    username: str | None = None
    email: EmailStr | None = None
    password: str

    @model_validator(mode="after")
    def validate_login_method(self) -> Self:
        if not self.username and not self.email:
            raise LoginMethodRequiredError

        if self.username and self.email:
            raise LoginMethodAmbiguousError

        return self


class UserResponse(BaseModel):
    id: UUID
    username: str
    email: EmailStr
    first_name: str
    second_name: str
    avatar_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class UserListItem(BaseModel):
    """Безопасные данные пользователя для списка поиска."""

    id: UUID
    username: str
    first_name: str
    second_name: str
    avatar_url: str | None = None

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=50)
    email: EmailStr | None = Field(default=None)
    password: str | None = Field(default=None)
    first_name: str | None = Field(default=None, min_length=1, max_length=50)
    second_name: str | None = Field(default=None, min_length=1, max_length=50)
    avatar_url: str | None = Field(default=None)
