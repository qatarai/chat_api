"""Streaming helpers for sending content in chunks (text or bytes).

Provides lightweight synchronous handle class used by
clients to send subsequent chunks and signal the end of a stream. Validation of
stream eligibility is the responsibility of the caller (e.g., clients), not the
handles themselves.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, Optional, TypeVar

from .models import ID

T = TypeVar("T")


@dataclass
class StreamHandle(Generic[T]):
    """Synchronous stream handle for sending chunks of any type.

    Attributes:
        content_id: The content id of the stream.
        send: Function to send a chunk (text or bytes).
        end: Callback invoked when the stream ends.
    """

    content_id: Optional[ID]
    send: Callable[[T], None]
    end: Callable[[], None]
