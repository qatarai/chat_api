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

from ..asyncio import AsyncioMixin
from .base import Transport


class StarletteTransport(Transport, AsyncioMixin):
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

        self.recv_loop()

    def recv_loop(self) -> None:
        """Start the background receive loop.

        Creates a task on the event loop which repeatedly awaits
        `websocket.receive()` and forwards any text/bytes payloads to
        `msg_received`.
        """

        async def _recv_loop() -> None:
            while True:
                message = await self._websocket.receive()
                if "text" in message and message["text"] is not None:
                    self.notify_msg_received_listeners(message["text"])
                elif "bytes" in message and message["bytes"] is not None:
                    self.notify_msg_received_listeners(message["bytes"])

        loop = self.ensure_loop()
        self._recv_task = loop.create_task(_recv_loop())

    def send_text_impl(self, data: str) -> Optional[asyncio.Task[None]]:
        return self.run_coroutine(self._websocket.send_text(data))

    def send_bytes_impl(self, data: bytes) -> Optional[asyncio.Task[None]]:
        return self.run_coroutine(self._websocket.send_bytes(data))

    def close(self) -> Optional[asyncio.Task[None]]:
        if self._recv_task and not self._recv_task.done():
            self._recv_task.cancel()

        task = self.run_coroutine(self._websocket.close())
        super().close()
        return task
