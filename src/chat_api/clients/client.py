"""Synchronous client for sending client->server messages with validation."""

from __future__ import annotations

from asyncio import Task
from typing import Callable, Optional, Tuple

from ..clients.base import Base
from ..models import (
    ID,
    Config,
    Event,
    InputEnd,
    InputMedia,
    InputText,
    Interrupt,
    OutputContent,
    OutputContentAddition,
    OutputEnd,
    OutputFunctionCall,
    OutputMedia,
    OutputStage,
    OutputText,
    OutputTranscription,
    ServerReady,
)
from ..states.client import ClientRequestState
from ..streaming import SendStreamHandle
from ..transports import Transport


class Client(Base):
    """Synchronous client for sending client->server messages with validation."""

    def __init__(
        self,
        transport: Transport,
        event_callback: Callable[[Client, Event], None],
        config: Config = Config(),
    ) -> None:
        """Initialize the client.

        Args:
            transport: The transport used to send events and media.
            event_callback: The callback to call when an event is received.
            config: The configuration for the client.
        """
        # Used for type-hinting
        self._request_state: ClientRequestState = ClientRequestState()

        super().__init__(
            request_state=self._request_state,
            transport=transport,
        )

        self._config = config
        self._request_id: Optional[ID] = None
        self.event_callback = event_callback

        # Set the parse media uuid flag to True
        self._transport.set_is_client(True)

        # Register callback for incoming events
        self._transport.on_event_received(self.event_received_callback)

        # Send config
        self._transport.send_event(self._config)

    def event_received_callback(self, evt: Event) -> None:
        """Handle an incoming event."""
        if isinstance(evt, ServerReady):
            self._config.chat_id = evt.chat_id
            self._request_id = evt.request_id
            self._request_state.ready(self._config)

        elif isinstance(evt, InputEnd):
            self._request_state.end_input()

        elif isinstance(evt, OutputEnd):
            self.close()

        elif isinstance(evt, Interrupt):
            self._request_state.interrupt()
            self.close()

        if isinstance(
            evt,
            (
                ServerReady,
                OutputTranscription,
                InputEnd,
                OutputStage,
                OutputContent,
                OutputContentAddition,
                OutputText,
                OutputFunctionCall,
                OutputMedia,
                OutputEnd,
                Interrupt,
            ),
        ):
            self.event_callback(self, evt)

    def text(self, data: str) -> Tuple[InputText, Optional[Task[None]]]:
        """Send InputText."""
        self._request_state.text()
        evt = InputText(data=data)
        task = self._transport.send_event(evt)
        return evt, task

    def media_stream(
        self,
    ) -> SendStreamHandle[bytes]:
        """Start sending raw audio input bytes to the server."""

        def send(data: bytes) -> Tuple[InputMedia, Optional[Task[None]]]:
            self._request_state.media()
            evt = InputMedia(data=data)
            task = self._transport.send_bytes(evt.data)
            return evt, task

        def end() -> Tuple[Optional[InputEnd], Optional[Task[None]]]:
            return self.end_input()

        return SendStreamHandle[bytes](
            content_id=None,
            send=send,
            end=end,
        )
