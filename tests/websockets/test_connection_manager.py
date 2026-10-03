from __future__ import annotations

from typing import cast
from uuid import uuid4

import pytest
from fastapi import WebSocket

from socket_app.connection_manager import connection_manager


class FakeSocket:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.sent: list[str] = []

    async def send_text(self, payload: str) -> None:
        if self.fail:
            raise RuntimeError("socket is closed")
        self.sent.append(payload)


@pytest.mark.asyncio
async def test_send_to_users_skips_failed_socket() -> None:
    first_user, second_user, offline_user = uuid4(), uuid4(), uuid4()
    broken = FakeSocket(fail=True)
    first_tab = FakeSocket()
    second_tab = FakeSocket()
    other_user_tab = FakeSocket()
    connection_manager.connections[first_user] = cast(
        "set[WebSocket]", {broken, first_tab, second_tab}
    )
    connection_manager.connections[second_user] = cast(
        "set[WebSocket]", {other_user_tab}
    )

    await connection_manager.send_to_users(
        {first_user, second_user, offline_user},
        "payload",
    )

    assert first_tab.sent == ["payload"]
    assert second_tab.sent == ["payload"]
    assert other_user_tab.sent == ["payload"]
