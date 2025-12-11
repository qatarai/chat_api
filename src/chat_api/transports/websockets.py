"""Websockets transport implementation."""

from websockets.exceptions import ConnectionClosed
from websockets.sync.connection import Connection

from .base import Transport


class WebsocketsTransport(Transport):
    """Websockets transport implementation."""

    def __init__(self, websocket: Connection, is_client: bool = False) -> None:
        self.websocket = websocket
        super().__init__(is_client=is_client)

    def send_impl(self, data: str | bytes) -> None:
        self.websocket.send(data)

    def receive_impl(self) -> str | bytes | None:
        try:
            return self.websocket.recv()
        except ConnectionClosed:
            return None

    def close(self) -> None:
        self.websocket.close()
        super().close()
