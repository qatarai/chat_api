"""In-memory transport useful for tests/examples."""

from typing import Any, Coroutine, Optional

from .base import Transport


class InMemoryTransport(Transport):
    """In-memory transport useful for tests/examples."""

    def __init__(self) -> None:
        super().__init__()
        self._text_queue: list[str] = []
        self._bytes_queue: list[bytes] = []

    async def recv_loop(self) -> None:
        """Receive loop."""
        return None

    def send_text_impl(self, data: str) -> None:
        self._text_queue.append(data)

    def send_bytes_impl(self, data: bytes) -> None:
        self._bytes_queue.append(data)

    def close_impl(self) -> Optional[Coroutine[Any, Any, None]]:
        """Close the transport."""
        self._text_queue.clear()
        self._bytes_queue.clear()
        return None
