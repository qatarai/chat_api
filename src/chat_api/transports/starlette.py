"""Starlette/FastAPI transport implementation."""

import asyncio

from starlette.websockets import WebSocket
from websockets import ConnectionClosed

from .base import Transport


class StarletteTransport(Transport):
    """Starlette/FastAPI transport implementation."""

    def __init__(self, websocket: WebSocket, is_client: bool = False) -> None:
        self.websocket = websocket
        self.loop = asyncio.get_event_loop()
        super().__init__(is_client=is_client)

    def send_impl(self, data: str | bytes) -> None:
        asyncio.run_coroutine_threadsafe(
            self.websocket.send_text(data)
            if isinstance(data, str)
            else self.websocket.send_bytes(data),
            self.loop,
        ).result()

    def receive_impl(self) -> str | bytes | None:
        try:
            message = asyncio.run_coroutine_threadsafe(
                self.websocket.receive(),
                self.loop,
            ).result()
        except ConnectionClosed:
            return None

        if "text" in message:
            return message["text"]
        elif "bytes" in message:
            return message["bytes"]
        else:
            return None
