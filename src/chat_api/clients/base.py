"""Shared logic for Chat API clients (sync and async).

Provides state management, validation, and event-building helpers that do not
perform any I/O. Concrete clients are responsible only for sending the prepared
payloads over their respective transports.
"""

from __future__ import annotations

from abc import ABC
from asyncio import Task
from typing import Optional, Tuple

from ..enums import InterruptType
from ..models import ID, InputEnd, Interrupt, new_id
from ..states import RequestState
from ..transports import Transport


class Base(ABC):
    """Base class for server and client implementations.

    Holds request state and common helpers. Concrete clients are responsible
    only for sending the prepared payloads over their respective transports.
    """

    def __init__(
        self,
        request_state: RequestState,
        transport: Transport,
    ) -> None:
        """Initialize the client.

        Sets up a fresh `RequestState` instance and an internal mapping from
        output `content_id` values to 16-byte UUIDs used for media stream
        chunk identifiers.
        """
        self._request_state = request_state
        self._transport = transport

    @staticmethod
    def new_uuid() -> ID:
        """Generate a random ID.

        Returns:
            ID: A new RFC 4122 random ID.
        """
        return new_id()

    def end_input(self) -> Tuple[InputEnd, Optional[Task[None]]]:
        """End the input."""
        self._request_state.end_input()
        evt = InputEnd()
        task = self._transport.send_event(evt)
        return evt, task

    def interrupt(
        self,
        interrupt_type: InterruptType,
    ) -> Tuple[Interrupt, Optional[Task[None]]]:
        """Interrupt the request."""
        self._request_state.interrupt()
        evt = Interrupt(interrupt_type=interrupt_type)
        task = self._transport.send_event(evt)
        return evt, task
