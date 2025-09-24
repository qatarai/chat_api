"""Abstract transport interfaces."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Callable, Set

from pydantic import BaseModel

from chat_api.models import Event
from chat_api.parsing import parse_bytes_event, parse_text_event


class Transport(ABC):
    """Synchronous transport interface.

    Implementations must provide send_text, send_bytes, and receive loop that
    calls `msg_received` when inbound messages arrive.
    """

    def __init__(self) -> None:
        self.on_event_received_callbacks: Set[Callable[[Event], None]] = set()
        self.on_event_sent_callbacks: Set[Callable[[Event], None]] = set()

    @abstractmethod
    def _send_text(self, data: str) -> None:  # pragma: no cover - abstract
        raise NotImplementedError()

    @abstractmethod
    def _send_bytes(self, data: bytes) -> None:  # pragma: no cover - abstract
        raise NotImplementedError()

    def send_text(self, data: str) -> None:
        """Send text data to the transport."""
        self._send_text(data)
        self.msg_sent(data)

    def send_bytes(self, data: bytes) -> None:
        """Send bytes data to the transport."""
        self._send_bytes(data)
        self.msg_sent(data)

    def send_json(self, obj: BaseModel | dict) -> None:
        """Send JSON data to the transport."""
        payload = (
            obj.model_dump_json()
            if isinstance(obj, BaseModel)
            else json.dumps(obj)
        )
        self._send_text(payload)
        if isinstance(obj, Event):
            self.event_sent(obj)
        else:
            self.msg_sent(payload)

    def notify_event_sent_listeners(self, data: Event) -> None:
        """Notify all event sent listeners."""
        for callback in self.on_event_sent_callbacks:
            callback(data)

    def on_event_sent(self, callback: Callable[[Event], None]) -> None:
        """Add an event sent listener."""
        self.on_event_sent_callbacks.add(callback)

    def notify_event_received_listeners(self, data: Event) -> None:
        """Notify all event received listeners."""
        for callback in self.on_event_received_callbacks:
            callback(data)

    def on_event_received(self, callback: Callable[[Event], None]) -> None:
        """Add an event received listener."""
        self.on_event_received_callbacks.add(callback)

    def parse_event(self, data: str | bytes) -> Event:
        """Parse the event from the data."""
        if isinstance(data, str):
            return parse_text_event(data)
        elif isinstance(data, bytes):
            return parse_bytes_event(data, is_input=True)
        else:
            raise ValueError(f"Unknown message type: {type(data)}")

    def msg_received(self, data: str | bytes) -> None:
        """Received a message from the transport."""
        evt = self.parse_event(data)
        self.event_received(evt)

    def msg_sent(self, data: str | bytes) -> None:
        """Sent a message to the transport."""
        evt = self.parse_event(data)
        self.event_sent(evt)

    def event_received(self, evt: Event) -> None:
        """Received an event from the transport."""
        self.notify_event_received_listeners(evt)

    def event_sent(self, evt: Event) -> None:
        """Sent an event to the transport."""
        self.notify_event_sent_listeners(evt)

    def __del__(self) -> None:
        """Clear all event listeners."""
        self.on_event_received_callbacks.clear()
        self.on_event_sent_callbacks.clear()


class InMemoryTransport(Transport):
    """In-memory transport useful for tests/examples."""

    def __init__(self) -> None:
        super().__init__()
        self._text_queue: list[str] = []
        self._bytes_queue: list[bytes] = []

    def _send_text(self, data: str) -> None:
        self._text_queue.append(data)

    def _send_bytes(self, data: bytes) -> None:
        self._bytes_queue.append(data)
