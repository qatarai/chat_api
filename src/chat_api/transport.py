"""Abstract transport interfaces and in-memory test transports."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Callable, Set

from pydantic import BaseModel

from chat_api.models import Event
from chat_api.parsing import parse_bytes_event, parse_text_event


class Transport(ABC):
    """Synchronous transport interface.

    Implementations must provide send_text, send_bytes, and receive iterators.
    A helper send_json serializes any Python object to JSON and calls send_text.

    Important:
        - The transport is not thread-safe. Safe use requires external synchronization.
        - The `msg_received` must be called by the user when a message is received.

    Attributes:
        on_event_received_callbacks: Set of callbacks for incoming events.
        on_event_sent_callbacks: Set of callbacks for outgoing events.
    """

    def __init__(self) -> None:
        """Initialize the transport."""
        self.on_event_received_callbacks: Set[Callable[[Event], None]] = set()
        """Set of callbacks for incoming events."""
        self.on_event_sent_callbacks: Set[Callable[[Event], None]] = set()
        """Set of callbacks for outgoing events."""

    @abstractmethod
    def _send_text(self, data: str) -> None:
        """Send a text frame.

        Args:
            data: The text payload.
        """
        raise NotImplementedError()

    @abstractmethod
    def _send_bytes(self, data: bytes) -> None:
        """Send a bytes frame.

        Args:
            data: The raw bytes payload.
        """
        raise NotImplementedError()

    def send_text(self, data: str) -> None:
        """Send a text frame."""
        self._send_text(data)
        self.msg_sent(data)

    def send_bytes(self, data: bytes) -> None:
        """Send a bytes frame."""
        self._send_bytes(data)
        self.msg_sent(data)

    def send_json(self, obj: BaseModel | dict) -> None:
        """Serialize and send a JSON payload over text channel.

        Args:
            obj: JSON-serializable data or Pydantic model.
        """
        self._send_text(
            obj.model_dump_json()
            if isinstance(obj, BaseModel)
            else json.dumps(obj)
        )

        if isinstance(obj, Event):
            self.event_sent(obj)
        else:
            self.msg_sent(json.dumps(obj))

    def notify_event_sent_listeners(self, data: Event) -> None:
        """Notify all event sent callbacks."""
        for callback in self.on_event_sent_callbacks:
            callback(data)

    def on_event_sent(self, callback: Callable[[Event], None]) -> None:
        """Register a callback for outgoing events."""
        self.on_event_sent_callbacks.add(callback)

    def notify_event_received_listeners(self, data: Event) -> None:
        """Notify all event received callbacks."""
        for callback in self.on_event_received_callbacks:
            callback(data)

    def on_event_received(self, callback: Callable[[Event], None]) -> None:
        """Register a callback for incoming events."""
        self.on_event_received_callbacks.add(callback)

    def parse_event(self, data: str | bytes) -> Event:
        """Parse an event from a message."""
        if isinstance(data, str):
            return parse_text_event(data)
        elif isinstance(data, bytes):
            return parse_bytes_event(data, is_input=True)
        else:
            raise ValueError(f"Unknown message type: {type(data)}")

    def msg_received(self, data: str | bytes) -> None:
        """This method must be called by the transport
        implementation when a message is received."""
        evt = self.parse_event(data)
        self.event_received(evt)

    def msg_sent(self, data: str | bytes) -> None:
        """This method must be called by the transport
        implementation when a message is sent."""
        evt = self.parse_event(data)
        self.event_sent(evt)

    def event_received(self, evt: Event) -> None:
        """This method must be called by the transport
        implementation when an event is received."""
        self.notify_event_received_listeners(evt)

    def event_sent(self, evt: Event) -> None:
        """This method must be called by the transport
        implementation when an event is sent."""
        self.notify_event_sent_listeners(evt)

    def __del__(self) -> None:
        """Clean up the transport."""
        self.on_event_received_callbacks.clear()
        self.on_event_sent_callbacks.clear()


class InMemoryTransport(Transport):
    """In-memory transport useful for tests/examples.

    Uses two internal queues (lists) for text and bytes. Iterators drain them.
    """

    def __init__(self) -> None:
        """Initialize with empty text and bytes queues."""
        super().__init__()
        self._text_queue: list[str] = []
        self._bytes_queue: list[bytes] = []

    def _send_text(self, data: str) -> None:
        """Append a text frame to the queue."""
        self._text_queue.append(data)

    def _send_bytes(self, data: bytes) -> None:
        """Append a bytes frame to the queue."""
        self._bytes_queue.append(data)
