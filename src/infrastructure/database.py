from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, NoReturn

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import settings
from exc import DatabaseError, DatabaseWriteError

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

# 2. Создание асинхронного движка (Engine)
# echo=True будет выводить все SQL-запросы в консоль (полезно при разработке)
engine = create_async_engine(settings.database_url, echo=True, future=True)


# 3. Создание фабрики асинхронных сессий
# expire_on_commit=False предотвращает ошибку при обращении к атрибутам объекта после ко
async_session_maker = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


@asynccontextmanager
async def get_read_session() -> AsyncGenerator[AsyncSession]:
    def prevent_modifications(*_args: object, **_kwargs: object) -> NoReturn:
        raise DatabaseWriteError

    async with async_session_maker() as session:
        session: AsyncSession
        session.flush = prevent_modifications
        try:
            yield session
        except SQLAlchemyError as e:
            await session.rollback()
            raise DatabaseError from e


@asynccontextmanager
async def get_write_session() -> AsyncGenerator[AsyncSession]:
    async with async_session_maker() as session:
        session: AsyncSession
        try:
            yield session
            await session.commit()
        except SQLAlchemyError as e:
            await session.rollback()
            raise DatabaseError from e
