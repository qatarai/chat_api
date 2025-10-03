"""Abstract transport interfaces."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Callable, Optional, Set

from chat_api.exceptions import ChatApiTransportError
from chat_api.models import Event
from chat_api.parsing import parse_bytes_event, parse_text_event


class Transport(ABC):
    """Transport interface.

    Implementations must provide `send_text_impl`, `send_bytes_impl`, and call
    `notify_msg_received_listeners` when inbound messages arrive.
    """

    def __init__(self) -> None:
        """Initialize the transport."""
        self.on_event_received_callbacks: Set[Callable[[Event], None]] = set()
        self.on_event_sent_callbacks: Set[Callable[[Event], None]] = set()
        self.parse_media_uuid: bool = False

    def set_parse_media_uuid(self, parse_media_uuid: bool) -> None:
        """Set the parse media uuid flag."""
        self.parse_media_uuid = parse_media_uuid

    @abstractmethod
    def send_text_impl(self, data: str) -> Optional[asyncio.Task[None]]:
        """The transport-specific implementation of sending text data.

        This method should not be called directly. Use `send_text` instead.
        """
        raise NotImplementedError()

    @abstractmethod
    def send_bytes_impl(self, data: bytes) -> Optional[asyncio.Task[None]]:
        """The transport-specific implementation of sending bytes data.

        This method should not be called directly. Use `send_bytes` instead.
        """
        raise NotImplementedError()

    def send_text(self, data: str) -> Optional[asyncio.Task[None]]:
        """Send text data."""
        task = self.send_text_impl(data)
        self.notify_msg_sent_listeners(data)
        return task

    def send_bytes(self, data: bytes) -> Optional[asyncio.Task[None]]:
        """Send bytes data."""
        task = self.send_bytes_impl(data)
        self.notify_msg_sent_listeners(data)
        return task

    def send_event(self, obj: Event) -> Optional[asyncio.Task[None]]:
        """Send JSON data."""
        task = self.send_text_impl(obj.model_dump_json())
        self.notify_event_sent_listeners(obj)
        return task

    def on_event_received(self, callback: Callable[[Event], None]) -> None:
        """Add an event received listener."""
        self.on_event_received_callbacks.add(callback)

    def on_event_sent(self, callback: Callable[[Event], None]) -> None:
        """Add an event sent listener."""
        self.on_event_sent_callbacks.add(callback)

    def notify_msg_received_listeners(self, data: str | bytes) -> None:
        """Received a message from the transport."""
        evt = self.parse_event(data)
        self.notify_event_received_listeners(evt)

    def notify_msg_sent_listeners(self, data: str | bytes) -> None:
        """Sent a message to the transport."""
        evt = self.parse_event(data)
        self.notify_event_sent_listeners(evt)

    def notify_event_received_listeners(self, data: Event) -> None:
        """Notify all event received listeners."""
        for callback in self.on_event_received_callbacks:
            callback(data)

    def notify_event_sent_listeners(self, data: Event) -> None:
        """Notify all event sent listeners."""
        for callback in self.on_event_sent_callbacks:
            callback(data)

    def parse_event(self, data: str | bytes) -> Event:
        """Parse the event from the data."""
        if isinstance(data, str):
            return parse_text_event(data)
        elif isinstance(data, bytes):
            return parse_bytes_event(
                data,
                parse_media_uuid=self.parse_media_uuid,
            )
        else:
            raise ChatApiTransportError(f"Unknown message type: {type(data)}")

    @abstractmethod
    def close(self) -> Optional[asyncio.Task[None]]:
        """Release all resources, including event listeners."""
        self.on_event_received_callbacks.clear()
        self.on_event_sent_callbacks.clear()
        return None

    def __del__(self) -> None:
        """Release all resources, including event listeners."""
        self.close()
