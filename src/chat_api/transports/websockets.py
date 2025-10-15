"""Websockets transport implementation.

Requires the `websockets` extra.

This transport wraps a connected `websockets` protocol object and:
- Starts a receive loop that forwards inbound frames to `Transport.notify_msg_received_listeners`
- Schedules outbound text/bytes via the event loop
"""

from __future__ import annotations

import asyncio
from typing import Any, Coroutine, Optional

from websockets.asyncio.connection import Connection
from websockets.protocol import State as WebsocketsState

from ..asyncio import AsyncioMixin
from .base import Transport


class WebsocketsTransport(Transport, AsyncioMixin):
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
        self._websocket = websocket
        super().__init__(loop=loop)

    async def recv_loop(self) -> None:
        """Start the background receive loop.

        Creates an asyncio task on the target loop that reads messages from
        the websocket and calls `msg_received` for each one.
        """
        async for message in self._websocket:  # str or bytes
            self.notify_msg_received_listeners(message)

    def send_text_impl(self, data: str) -> Optional[asyncio.Task[None]]:
        return self.run_coroutine(self._websocket.send(data))

    def send_bytes_impl(self, data: bytes) -> Optional[asyncio.Task[None]]:
        return self.run_coroutine(self._websocket.send(data))

    def close_impl(self) -> Optional[Coroutine[Any, Any, None]]:
        if self._websocket.state == WebsocketsState.CLOSED:
            return None

        return self._websocket.close()
