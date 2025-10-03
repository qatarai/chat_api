"""Streaming helpers for sending content in chunks (text or bytes).

Provides lightweight synchronous handle class used by
clients to send subsequent chunks and signal the end of a stream. Validation of
stream eligibility is the responsibility of the caller (e.g., clients), not the
handles themselves.
"""

from __future__ import annotations

from asyncio import Task
from dataclasses import dataclass
from typing import (
    AsyncIterator,
    Callable,
    Generic,
    Optional,
    Tuple,
    TypeVar,
    Union,
)

from .models import ID, Event

T = TypeVar("T")


@dataclass
class SendStreamHandle(Generic[T]):
    """Stream handle for sending chunks of any type.

    Attributes:
        content_id: The content id of the stream.
        send: Function to send a chunk (text or bytes).
        end: Callback invoked when the stream ends.
    """

    content_id: Optional[ID]
    send: Callable[[T], Tuple[Event, Optional[Task[None]]]]
    end: Callable[[], Tuple[Optional[Event], Optional[Task[None]]]]


@dataclass
class ReceiveStreamHandle(Generic[T]):
    """Stream handle for receiving chunks of any type.

    Attributes:
        content_id: The content id of the stream.
        receive: Function to receive a chunk (text or bytes).
        end: Callback invoked when the stream ends.
    """

    content_id: Optional[ID]
    receive: Callable[[], Union[Task[T], T]]
    end: Callable[[], Tuple[Optional[Event], Optional[Task[None]]]]

    def __aiter__(self) -> AsyncIterator[T]:
        """Async iterator for the stream."""
        return self

    async def __anext__(self) -> T:
        """Receive the next chunk."""
        task = self.receive()

        if isinstance(task, Task):
            return await task

        return task
