"""Websockets transport implementation.

Requires the `websockets` extra.

This transport wraps a connected `websockets` protocol object and:
- Starts a receive loop that forwards inbound frames to `Transport.msg_received`
- Schedules outbound text/bytes via the event loop
"""

from __future__ import annotations

import asyncio
from typing import Optional

from websockets.asyncio.connection import Connection

from .base import Transport
from .scheduling import AsyncioSchedulingMixin


class WebsocketsTransport(Transport, AsyncioSchedulingMixin):
    """Transport backed by a `websockets` connection.

    Schedules async send operations and runs a background receive loop to
    forward incoming messages to `Transport.msg_received`.

    Args:
        websocket: A connected `websockets.asyncio.connection.Connection`.
        loop: Optional event loop to schedule tasks on. If omitted, uses the
              current running loop or falls back to blocking `asyncio.run`.
    """

    def __init__(
        self,
        websocket: Connection,
        loop: Optional[asyncio.AbstractEventLoop] = None,
    ) -> None:
        """Initialize the transport."""
        super().__init__()
        self._websocket = websocket
        self._loop = loop
        self._recv_task: Optional[asyncio.Task[None]] = None

        self.start()

    def start(self) -> None:
        """Start the background receive loop.

        Creates an asyncio task on the target loop that reads messages from
        the websocket and calls `msg_received` for each one.
        """

        async def _recv_loop() -> None:
            try:
                async for message in self._websocket:  # str or bytes
                    self.msg_received(message)
            finally:
                # Nothing to clean specifically here
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
        self._schedule_send(self._websocket.send(data))

    def _send_text(self, data: str) -> None:
        self._send_data(data)

    def _send_bytes(self, data: bytes) -> None:
        self._send_data(data)
