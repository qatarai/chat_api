"""Starlette/FastAPI transport implementation.

Requires the `fastapi` extra.

This transport wraps a `starlette.websockets.WebSocket` and:
- Starts a receive loop consuming `receive()` dicts and forwarding text/bytes
  to `Transport.msg_received`
- Schedules outbound `send_text`/`send_bytes` on an asyncio loop
"""

from __future__ import annotations

import asyncio
from typing import Optional

try:
    from starlette.websockets import WebSocket as StarletteWebSocket
except ImportError as e:
    raise ImportError(
        "StarletteTransport requires the 'starlette' extra.\n"
        "Install with: pip install chat_api[starlette]"
    ) from e

from .base import Transport
from .scheduling import AsyncioSchedulingMixin


class StarletteTransport(Transport, AsyncioSchedulingMixin):
    """Transport backed by Starlette/FastAPI `WebSocket`.

    Runs a background receive loop to forward messages to `Transport.msg_received`.
    Uses concrete `send_text` and `send_bytes` methods for sending.
    """

    def __init__(
        self,
        websocket: StarletteWebSocket,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        super().__init__()
        self._websocket = websocket
        self._loop = loop
        self._recv_task: Optional[asyncio.Task[None]] = None

        self.start()

    def start(self) -> None:
        """Start the background receive loop.

        Creates a task on the event loop which repeatedly awaits
        `websocket.receive()` and forwards any text/bytes payloads to
        `msg_received`.
        """

        async def _recv_loop() -> None:
            try:
                while True:
                    message = await self._websocket.receive()
                    if "text" in message and message["text"] is not None:
                        self.msg_received(message["text"])
                    elif "bytes" in message and message["bytes"] is not None:
                        self.msg_received(message["bytes"])
                    # ignore other message types like 'ping', 'close' here
            finally:
                pass

        loop = self._ensure_loop()
        self._recv_task = loop.create_task(_recv_loop())

    def close(self) -> None:
        """Cancel the background receive loop.

        Note: this does not close the underlying websocket connection.
        """
        if self._recv_task and not self._recv_task.done():
            self._recv_task.cancel()

    def _send_data(self, data: str | bytes) -> None:
        if isinstance(data, str):
            coro = self._websocket.send_text(data)
        else:
            coro = self._websocket.send_bytes(data)
        self._schedule_send(coro)

    def _send_text(self, data: str) -> None:
        self._send_data(data)

    def _send_bytes(self, data: bytes) -> None:
        self._send_data(data)
