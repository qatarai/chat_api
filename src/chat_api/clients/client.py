"""Synchronous client for sending client->server messages with validation."""

from __future__ import annotations

from typing import Callable, Optional

from ..enums import InterruptType
from ..models import Config, Event, InputEnd, InputInterrupt, InputText
from ..streaming import StreamHandle
from ..transport import Transport


class ClientToServer:
    """Synchronous client for sending client->server messages with validation."""

    def __init__(
        self,
        transport: Transport,
        config: Config = Config(),
        on_output: Optional[Callable[[ClientToServer, Event], None]] = None,
    ) -> None:
        """Initialize the client.

        Args:
            transport: The transport used to send events and media.
            config: The configuration for the client.
            on_output: The callback to call when an output event is received.
        """
        self._tx = transport
        self._config = config
        self._on_output = on_output

        # Register callback for incoming events
        self._tx.on_event_received(self._on_event)

        # Send config
        self._tx.send_json(self._config)

    def _on_event(self, evt: Event) -> None:
        """Handle an incoming event."""
        if self._on_output:
            self._on_output(self, evt)

    def on_output(
        self,
        callback: Callable[[ClientToServer, Event], None],
    ) -> None:
        """Set the callback for output events."""
        self._on_output = callback

    def text(self, data: str) -> None:
        """Send InputText."""
        evt = InputText(data=data)
        self._tx.send_json(evt)

    def media_stream(self) -> StreamHandle[bytes]:
        """Start sending raw audio input bytes to the server.

        Returns:
            StreamHandle[bytes]: A handle with send and end methods.
        """

        def send(data: bytes) -> None:
            self._tx.send_bytes(data)

        def end() -> None:
            self.end()

        return StreamHandle[bytes](
            content_id=None,
            send=send,
            end=end,
        )

    def end(self) -> None:
        """Send InputEnd."""
        self._tx.send_json(InputEnd())

    def interrupt(
        self, interrupt_type: InterruptType = InterruptType.USER
    ) -> None:
        """Send InputInterrupt."""
        self._tx.send_json(InputInterrupt(interrupt_type=interrupt_type))
