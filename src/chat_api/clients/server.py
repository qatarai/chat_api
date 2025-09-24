"""Synchronous clients for Chat API (server->client and client->server)."""

from __future__ import annotations

from typing import Any, Callable, Dict, Literal, Optional

from ..enums import ContentType
from ..models import (
    ID,
    Config,
    Event,
    InputEnd,
    InputInterrupt,
    InputMedia,
    InputText,
    OutputContent,
    OutputEnd,
    OutputFunctionCall,
    OutputInitialization,
    OutputStage,
)
from ..streaming import StreamHandle
from ..transports import Transport
from .shared import _ServerToClientShared


class ServerToClient(_ServerToClientShared):
    """Synchronous client for sending server->client events with validation.

    Transport must be provided by caller and is used for sending text (JSON)
    and bytes (media).
    """

    def __init__(
        self,
        transport: Transport,
        stop_automatic_handling: bool = False,
        on_input: Optional[
            Callable[
                [
                    ServerToClient,
                    InputText | InputMedia | InputEnd | InputInterrupt,
                ],
                None,
            ]
        ] = None,
    ) -> None:
        """Initialize the client.

        Args:
            transport: The transport used to send events and media.
            stop_automatic_handling: Whether to stop automatic handling of events
                received from the client. If False (default), the events are
                automatically parsed, validated, and responded to.
            on_input: Optional callback to handle input events.
        """
        super().__init__()
        self._tx = transport

        if not stop_automatic_handling:
            self._tx.on_event_received(self._on_event)

        self._on_input = on_input

    #######################################################
    # Receiving events
    #######################################################
    def _on_event(self, evt: Event) -> None:
        """Handle a client->server event."""
        if isinstance(evt, Config):
            self._on_config(evt)
        elif isinstance(
            evt, (InputText, InputMedia, InputEnd, InputInterrupt)
        ):
            if self._on_input is not None:
                self._on_input(self, evt)
        else:
            raise ValueError(f"Unexpected event type: {evt.event_type}")

    def _on_config(self, evt: Config) -> None:
        """Handle a Config event."""
        self.initialize(config=evt)

    def on_input(
        self,
        callback: Callable[
            [
                ServerToClient,
                InputText | InputMedia | InputEnd | InputInterrupt,
            ],
            None,
        ],
    ) -> None:
        """Set the callback for input events."""
        self._on_input = callback

    #######################################################
    # Sending events
    #######################################################

    def _ensure_output_content(
        self,
        *,
        content_type: ContentType,
        stage_id: ID,
        content_id: Optional[ID],
    ) -> OutputContent:
        """Ensure content exists; send OutputContent if it was not already sent.

        Returns a content that is ensured to exist.
        """
        content_evt, should_send = self._get_output_content_state(
            content_id=content_id,
            content_type=content_type,
            stage_id=stage_id,
        )

        if should_send:
            self._tx.send_json(content_evt)

        return content_evt

    def initialize(
        self,
        *,
        config: Config,
        request_id: Optional[ID] = None,
    ) -> OutputInitialization:
        """Send OutputInitialization and mark the request initialized.

        Args:
            config: The config to send.
            request_id: Optional existing request id. If not provided a new one is generated.

        Returns:
            OutputInitialization: The initialization event sent.
        """
        evt = self._prepare_output_initialization(
            chat_id=config.chat_id,
            request_id=request_id,
        )

        # Maintain state
        config.chat_id = evt.chat_id
        self._state.initialize(
            config=config,
            request_id=evt.request_id,
        )

        # Send event
        self._tx.send_json(evt)

        return evt

    def end_input(self) -> None:
        """InputEnd event to signal the end of the input stream."""
        # Maintain state
        self._state.end_input()

        # Send event
        self._tx.send_json(InputEnd())

    def stage(
        self,
        *,
        title: str,
        description: str,
        stage_id: Optional[ID] = None,
        parent_id: Optional[ID] = None,
    ) -> OutputStage:
        """Send an OutputStage event.

        Args:
            title: Stage title.
            description: Stage description.
            stage_id: Optional stage id to use; generates one if not provided.
            parent_id: Optional parent stage id.

        Returns:
            OutputStage: The stage sent.
        """
        evt = self._prepare_output_stage(
            title=title,
            description=description,
            stage_id=stage_id,
            parent_id=parent_id,
        )

        # Maintain state
        self._state.add_stage(evt)

        # Send event
        self._tx.send_json(evt)

        return evt

    def content(
        self,
        *,
        content_type: ContentType,
        stage_id: ID,
        content_id: Optional[ID] = None,
    ) -> OutputContent:
        """Send an OutputContent event for a stage.

        Args:
            content_type: The content type of the new content.
            stage_id: The stage receiving the content.
            content_id: Optional content id to use; generates one if omitted.

        Returns:
            OutputContent: The content sent.
        """
        evt = self._prepare_output_content(
            content_id=content_id,
            content_type=content_type,
            stage_id=stage_id,
        )

        # Maintain state
        self._state.add_content(evt)

        # Send event
        self._tx.send_json(evt)

        return evt

    def content_addition(
        self,
        *,
        content_id: ID,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Send an OutputContentAddition for an existing content item.

        Args:
            content_id: The id of the existing content.
            metadata: Optional additional metadata.
        """
        evt = self._prepare_output_content_addition(
            content_id=content_id,
            metadata=metadata,
        )

        # Maintain state
        self._state.add_content_addition(evt)

        # Send event
        self._tx.send_json(evt)

    def function_call(
        self,
        *,
        stage_id: ID,
        content_id: Optional[ID] = None,
        json_data: str,
    ) -> OutputFunctionCall:
        """Send an OutputFunctionCall event, ensuring content exists or creating it.

        Args:
            stage_id: The stage receiving the function call.
            content_id: Optional existing content id.
            json_data: Opaque JSON string representing the function call payload.

        Returns:
            OutputFunctionCall: The function call sent.
        """
        content_evt = self._ensure_output_content(
            content_type=ContentType.FUNCTION_CALL,
            stage_id=stage_id,
            content_id=content_id,
        )

        evt = self._prepare_output_function_call(
            content_id=content_evt.id,
            json_data=json_data,
        )

        # Maintain state
        self._state.add_function_call(content_id=content_evt.id)

        # Send event
        self._tx.send_json(evt)

        return evt

    def end(self) -> None:
        """Send OutputEnd and close the request if all streams are closed.

        Raises:
            ChatApiStateError: If any media streams are still open.
        """
        # Maintain state
        self._state.end_output()

        # Send event
        self._tx.send_json(OutputEnd())

    def text_stream(
        self,
        *,
        stage_id: ID,
        content_id: Optional[ID] = None,
    ) -> StreamHandle[str]:
        """Start a text stream by sending OutputContent and first OutputText.

        Args:
            stage_id: The target stage.
            content_id: Optional pre-defined content id.

        Returns:
            StreamHandle[str]: A handle with send and end methods.
        """
        content_evt = self._ensure_output_content(
            content_type=ContentType.TEXT,
            stage_id=stage_id,
            content_id=content_id,
        )

        # Maintain state
        self._state.open_stream(content_id=content_evt.id)

        def send(data: str) -> None:
            evt = self._prepare_output_text(
                content_id=content_evt.id,
                data=data,
            )

            self._tx.send_json(evt)

        def end() -> None:
            self._state.close_stream(content_id=content_evt.id)

        stream_handle = StreamHandle[str](
            content_id=content_evt.id,
            send=send,
            end=end,
        )

        return stream_handle

    def media_stream(
        self,
        *,
        content_type: Literal[ContentType.AUDIO, ContentType.VIDEO],
        stage_id: ID,
        content_id: Optional[ID] = None,
    ) -> StreamHandle[bytes]:
        """Start a binary media stream (audio or video).

        Args:
            content_type: Must be AUDIO or VIDEO.
            stage_id: The target stage id.
            content_id: Optional pre-defined content id.

        Returns:
            StreamHandle[bytes]: A handle with send and end methods.

        Raises:
            ChatApiValidationError: If content_type is not supported.
        """
        content_evt = self._ensure_output_content(
            content_type=content_type,
            stage_id=stage_id,
            content_id=content_id,
        )

        # Maintain state
        self._state.open_stream(content_id=content_evt.id)

        def send(data: bytes) -> None:
            evt = self._prepare_output_media(
                content_id=content_evt.id,
                data=data,
            )

            self._tx.send_bytes(evt.bytes())

        def end() -> None:
            self._state.close_stream(content_id=content_evt.id)

        return StreamHandle[bytes](
            content_id=content_evt.id,
            send=send,
            end=end,
        )
