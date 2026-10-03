"""Точка входа: собирает FastAPI-приложение из HTTP- и WebSocket-роутеров."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.exception_handlers import setup_exception_handlers
from api.v1.auth import auth_router
from api.v1.chat import chat_router
from api.v1.user import user_router
from config import settings
from socket_app.endpoint import websocket_router
from socket_app.presence_manager import presence_manager
from workers.taskiq.base import broker

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    await broker.startup()
    yield
    await presence_manager.shutdown()
    await broker.shutdown()


# Frontend в разработке ходит через прокси Vite (тот же origin);
# прямые запросы от dev-сервера разрешены для отладки.
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
)
setup_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user_router)
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(websocket_router)
