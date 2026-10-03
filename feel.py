from __future__ import annotations

import asyncio

from sqlalchemy import select

from infrastructure.database import get_write_session
from infrastructure.models import User
from utils import hash_password


def build_password(username: str) -> str:
    return f"{username.title()}12345!"


def get_users() -> list[User]:
    return [
        User(
            username="admin",
            first_name="Administrator",
            second_name="OpenVerse",
            email="admin@example.com",
            hashed_password=hash_password(build_password("admin")),
        ),
        User(
            username="anna",
            first_name="Anna",
            second_name="Ivanova",
            email="anna@example.com",
            hashed_password=hash_password(build_password("anna")),
        ),
        User(
            username="max",
            first_name="Max",
            second_name="Petrov",
            email="max@example.com",
            hashed_password=hash_password(build_password("max")),
        ),
        User(
            username="olga",
            first_name="Olga",
            second_name="Sidorova",
            email="olga@example.com",
            hashed_password=hash_password(build_password("olga")),
        ),
        User(
            username="ivan",
            first_name="Ivan",
            second_name="Smirnov",
            email="ivan@example.com",
            hashed_password=hash_password(build_password("ivan")),
        ),
        User(
            username="sofia",
            first_name="Sofia",
            second_name="Volkova",
            email="sofia@example.com",
            hashed_password=hash_password(build_password("sofia")),
        ),
        User(
            username="daniil",
            first_name="Daniil",
            second_name="Kuznetsov",
            email="daniil@example.com",
            hashed_password=hash_password(build_password("daniil")),
        ),
        User(
            username="maria",
            first_name="Maria",
            second_name="Popova",
            email="maria@example.com",
            hashed_password=hash_password(build_password("maria")),
        ),
    ]


async def seed_users() -> int:
    users = get_users()
    usernames = tuple(user.username for user in users)
    emails = tuple(user.email for user in users)

    async with get_write_session() as session:
        existing_usernames = set(
            await session.scalars(
                select(User.username).where(User.username.in_(usernames))
            )
        )
        existing_emails = set(
            await session.scalars(select(User.email).where(User.email.in_(emails)))
        )
        users_to_add = [
            user
            for user in users
            if user.username not in existing_usernames
            and user.email not in existing_emails
        ]
        session.add_all(users_to_add)

    return len(users_to_add)


if __name__ == "__main__":
    asyncio.run(seed_users())
