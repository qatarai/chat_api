"""Synchronous clients for Chat API (server->client and client->server)."""

from __future__ import annotations

import asyncio
from asyncio import Task
from typing import Any, Callable, Dict, Literal, Optional, Tuple

from ..enums import ContentType
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
    Transcription,
)
from ..states import ServerRequestState
from ..streaming import SendStreamHandle
from ..transports import Transport
from .base import Base


class Server(Base):
    """Server.

    Transport must be provided by caller and is used for receiving events.
    """

    def __init__(
        self,
        transport: Transport,
        event_callback: Callable[
            [
                Server,
                Config | InputText | InputMedia | InputEnd | Interrupt,
            ],
            None,
        ],
    ) -> None:
        """Initialize the client.

        Args:
            transport: The transport used to communicate with the client.
            event_callback: Optional callback to handle input events.
        """
        # Used for type-hinting
        self._request_state: ServerRequestState = ServerRequestState()

        super().__init__(
            request_state=self._request_state,
            transport=transport,
        )

        self.event_callback = event_callback

        # Keep track of finish status
        self._finished = asyncio.Event()

        # Register callback for incoming events
        self._transport.on_event_received(self.event_received_callback)

    async def join(self) -> None:
        """Wait for the server to finish sending all queued actions/events."""
        await self._finished.wait()

    def event_received_callback(self, evt: Event) -> None:
        """Handle a client->server event."""
        if isinstance(evt, Config):
            self.ready(evt)

        elif isinstance(evt, InputEnd):
            self._request_state.end_input()

        elif isinstance(evt, Interrupt):
            self._request_state.interrupt()
            self._finished.set()

        if isinstance(
            evt, (Config, InputText, InputMedia, InputEnd, Interrupt)
        ):
            self.event_callback(self, evt)

    def ready(
        self,
        config: Config,
        request_id: Optional[ID] = None,
    ) -> Tuple[ServerReady, Optional[Task[None]]]:
        """Tell the client that the server is ready to receive input.

        Args:
            config: The config to send.
            request_id: Optional existing request id. If not provided a new one is generated.

        Returns:
            Tuple[ServerReady, Optional[Task[None]]]: The ready event sent and the task for sending it.
        """
        config.chat_id = config.chat_id or self.new_uuid()
        request_id = request_id or self.new_uuid()

        self._request_state.ready(config=config)

        evt = ServerReady(
            chat_id=config.chat_id,
            request_id=request_id,
        )
        task = self._transport.send_event(evt)
        return evt, task

    def transcription(
        self,
        transcription: Transcription,
    ) -> Tuple[OutputTranscription, Optional[Task[None]]]:
        """Send audio transcription."""
        self._request_state.transcription()
        evt = OutputTranscription(transcription=transcription)
        task = self._transport.send_event(evt)
        return evt, task

    def stage(
        self,
        title: str,
        description: str,
        stage_id: Optional[ID] = None,
    ) -> Tuple[OutputStage, Optional[Task[None]]]:
        """Send an OutputStage event."""
        stage_id = stage_id or self.new_uuid()
        evt = OutputStage(
            id=stage_id,
            title=title,
            description=description,
        )

        self._request_state.stage(evt)
        task = self._transport.send_event(evt)
        return evt, task

    def content(
        self,
        content_type: ContentType,
        stage_id: ID,
        content_id: Optional[ID] = None,
    ) -> Tuple[OutputContent, Optional[Task[None]]]:
        """Send an OutputContent event.

        Despite it NOT being the typical behavior of this class,
        if the content was already sent, the client won't raise an error.

        In the case that the content was not already sent, it will be sent.

        Returns:
            Tuple[OutputContent, Optional[Task[None]]]: The content sent and the task for sending it.
        """
        content_id = content_id or self.new_uuid()
        evt = OutputContent(
            id=content_id,
            type=content_type,
            stage_id=stage_id,
        )

        task = None
        if not self._request_state.has_content(evt):
            self._request_state.content(evt)
            task = self._transport.send_event(evt)

        return evt, task

    def content_addition(
        self,
        content_id: ID,
        metadata: Dict[str, Any],
    ) -> Tuple[OutputContentAddition, Optional[Task[None]]]:
        """Send an OutputContentAddition for an existing content item."""
        evt = OutputContentAddition(
            content_id=content_id,
            metadata=metadata,
        )
        self._request_state.content_addition(evt)
        task = self._transport.send_event(evt)
        return evt, task

    def function_call(
        self,
        stage_id: ID,
        json_data: str,
        content_id: Optional[ID] = None,
    ) -> Tuple[OutputFunctionCall, Optional[Task[None]]]:
        """Send an OutputFunctionCall event."""
        content_evt, task = self.content(
            content_type=ContentType.FUNCTION_CALL,
            stage_id=stage_id,
            content_id=content_id,
        )

        evt = OutputFunctionCall(
            content_id=content_evt.id,
            data=json_data,
        )
        self._request_state.function_call(evt)
        task = self._transport.send_event(evt)
        return evt, task

    def text_stream(
        self,
        *,
        stage_id: ID,
        content_id: Optional[ID] = None,
    ) -> Tuple[SendStreamHandle[str], Optional[Task[None]]]:
        """Start a text stream.

        Args:
            stage_id: The target stage.
            content_id: Optional pre-defined content id.

        Returns:
            Tuple[SendStreamHandle[str], Optional[Task[None]]]: A handle with send
                and end methods and the task for sending the content.
        """
        content_evt, task = self.content(
            content_type=ContentType.TEXT,
            stage_id=stage_id,
            content_id=content_id,
        )

        def send(data: str) -> Tuple[OutputText, Optional[Task[None]]]:
            evt = OutputText(
                content_id=content_evt.id,
                data=data,
            )
            self._request_state.text(evt)
            task = self._transport.send_event(evt)
            return evt, task

        def end() -> Tuple[Optional[OutputEnd], Optional[Task[None]]]:
            return None, None

        stream_handle = SendStreamHandle[str](
            content_id=content_evt.id,
            send=send,
            end=end,
        )
        return stream_handle, task

    def media_stream(
        self,
        *,
        content_type: Literal[ContentType.AUDIO, ContentType.VIDEO],
        stage_id: ID,
        content_id: Optional[ID] = None,
    ) -> Tuple[SendStreamHandle[bytes], Optional[Task[None]]]:
        """Start a binary media stream (audio or video).

        Args:
            content_type: Must be AUDIO or VIDEO.
            stage_id: The target stage id.
            content_id: Optional pre-defined content id.

        Returns:
            Tuple[SendStreamHandle[bytes], Optional[Task[None]]]: A handle with send
                and end methods and the task for sending the content.
        """
        content_evt, task = self.content(
            content_type=content_type,
            stage_id=stage_id,
            content_id=content_id,
        )

        def send(data: bytes) -> Tuple[OutputMedia, Optional[Task[None]]]:
            evt = OutputMedia(
                content_id=content_evt.id,
                data=data,
            )
            self._request_state.media(evt)
            task = self._transport.send_bytes(evt.get_bytes())
            return evt, task

        def end() -> Tuple[Optional[OutputEnd], Optional[Task[None]]]:
            return None, None

        stream_handle = SendStreamHandle[bytes](
            content_id=content_evt.id,
            send=send,
            end=end,
        )
        return stream_handle, task

    def end(self) -> Tuple[OutputEnd, Optional[Task[None]]]:
        """Tell the client that the server has finished sending output."""
        self._request_state.end()
        evt = OutputEnd()
        task = self._transport.send_event(evt)

        if task:
            task.add_done_callback(lambda _: self._finished.set())
        else:
            self._finished.set()

        return evt, task
