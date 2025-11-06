"""Synchronous clients for Chat API (server->client and client->server)."""

from __future__ import annotations

from asyncio import Task
from typing import Any, Callable, Dict, Optional, Tuple

from ..models import (
    ID,
    Config,
    Event,
    InputEnd,
    InputMedia,
    InputText,
    Interrupt,
    OutputAudioContent,
    OutputContent,
    OutputContentAddition,
    OutputEnd,
    OutputFunctionCall,
    OutputFunctionCallContent,
    OutputMedia,
    OutputStage,
    OutputText,
    OutputTextContent,
    OutputTranscription,
    OutputVideoContent,
    ServerReady,
    SessionEnd,
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
                Config
                | InputText
                | InputMedia
                | InputEnd
                | Interrupt
                | SessionEnd,
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

        # Register callback for incoming events
        self._transport.on_event_received(self.event_received_callback)

    def event_received_callback(self, evt: Event) -> None:
        """Handle a client->server event."""
        if isinstance(evt, Config):
            self.ready(evt)

        elif isinstance(evt, InputEnd):
            self._request_state.end_input()

        elif isinstance(evt, Interrupt):
            self._request_state.interrupt()
            self._request_state.reset()

        elif isinstance(evt, SessionEnd):
            self._request_state.end_session()
            self.close()

        if isinstance(
            evt,
            (
                Config,
                InputText,
                InputMedia,
                InputEnd,
                Interrupt,
                SessionEnd,
            ),
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
            Tuple[ServerReady, Optional[Task[None]]]: The ready event
                sent and the task for sending it.
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

    def text_content(
        self,
        stage_id: Optional[ID],
        content_id: Optional[ID] = None,
    ) -> Tuple[OutputContent, Optional[Task[None]]]:
        """Send an OutputTextContent event.

        Either content id or stage id must be provided.

        Args:
            stage_id: The target stage id.
            content_id: Optional pre-defined content id. If not provided a new one
                is generated.

        Returns:
            Tuple[OutputContent, Optional[Task[None]]]: The content event
                sent and the task for sending it. If the content has already been sent,
                the task is None.
        """
        content_id = content_id or self.new_uuid()
        content = self._request_state.has_content(content_id)

        if content:
            return content, None

        if not stage_id:
            raise ValueError(
                "Stage id must be provided when no content id is provided"
            )

        evt = OutputTextContent(
            id=content_id,
            stage_id=stage_id,
        )

        self._request_state.content(evt)
        task = self._transport.send_event(evt)

        return evt, task

    def function_call_content(
        self,
        stage_id: Optional[ID],
        content_id: Optional[ID] = None,
    ) -> Tuple[OutputContent, Optional[Task[None]]]:
        """Send an OutputFunctionCallContent event.

        Either content id or stage id must be provided.

        Args:
            stage_id: Target stage id.
            content_id: Optional pre-defined target content id. If not provided a new one
                is generated.

        Returns:
            Tuple[OutputContent, Optional[Task[None]]]: The content event
                sent and the task for sending it. If the content has already been sent,
                the task is None.
        """
        content_id = content_id or self.new_uuid()
        content = self._request_state.has_content(content_id)

        if content:
            return content, None

        if not stage_id:
            raise ValueError(
                "Stage id must be provided when no content id is provided"
            )

        evt = OutputFunctionCallContent(
            id=content_id,
            stage_id=stage_id,
        )

        self._request_state.content(evt)
        task = self._transport.send_event(evt)

        return evt, task

    def audio_content(
        self,
        stage_id: Optional[ID],
        nchannels: Optional[int],
        sample_rate: Optional[int],
        sample_width: Optional[int],
        content_id: Optional[ID] = None,
    ) -> Tuple[OutputContent, Optional[Task[None]]]:
        """Send an OutputAudioContent event.

        Either content id or (stage_id, nchannels, sample_rate, sample_width) must be provided.

        Args:
            stage_id: Target stage id.
            nchannels: Number of audio channels.
            sample_rate: Audio sample rate.
            sample_width: Sample width in bytes.
            content_id: Optional pre-defined target content id. If not provided a new one
            is generated.

        Returns:
            Tuple[OutputContent, Optional[Task[None]]]: The content event
                sent and the task for sending it. If the content has already been sent,
                the task is None.
        """
        content_id = content_id or self.new_uuid()
        content = self._request_state.has_content(content_id)

        if content:
            return content, None

        if (
            not stage_id
            or not nchannels
            or not sample_rate
            or not sample_width
        ):
            raise ValueError(
                "When no content id is provided, stage_id, nchannels, sample_rate and"
                " sample_width must be provided"
            )

        evt = OutputAudioContent(
            id=content_id,
            stage_id=stage_id,
            nchannels=nchannels,
            sample_rate=sample_rate,
            sample_width=sample_width,
        )

        self._request_state.content(evt)
        task = self._transport.send_event(evt)

        return evt, task

    def video_content(
        self,
        stage_id: Optional[ID],
        fps: Optional[int],
        width: Optional[int],
        height: Optional[int],
        content_id: Optional[ID] = None,
    ) -> Tuple[OutputContent, Optional[Task[None]]]:
        """Send an OutputVideoContent event.

        Either content id or (stage_id, fps, width, height) must be provided.

        Args:
            stage_id: Target stage id.
            fps: Video frames per second.
            width: Frame width.
            height: Frame height.
            content_id: Optional pre-defined target content id. If not provided a new one
                is generated.

        Returns:
            Tuple[OutputContent, Optional[Task[None]]]: The content event
                sent and the task for sending it. If the content has already been sent,
                the task is None.
        """
        content_id = content_id or self.new_uuid()
        content = self._request_state.has_content(content_id)

        if content:
            return content, None

        if not stage_id or not fps or not width or not height:
            raise ValueError(
                "When no content id is provided, stage_id, fps, width and height must be provided"
            )

        evt = OutputVideoContent(
            id=content_id,
            stage_id=stage_id,
            fps=fps,
            width=width,
            height=height,
        )

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
        json_data: str,
        stage_id: Optional[ID],
        content_id: Optional[ID] = None,
    ) -> Tuple[OutputFunctionCall, Optional[Task[None]]]:
        """Send an OutputFunctionCall event.

        Either content id or stage id must be provided.

        Args:
            json_data: The JSON data to send.
            stage_id: Target stage id.
            content_id: Optional pre-defined target content id. If not provided a new one
                is generated.

        Returns:
            Tuple[OutputFunctionCall, Optional[Task[None]]]: The function call event
                sent and the task for sending it. If the function call has already been sent,
                the task is None.
        """
        content_evt, task = self.function_call_content(
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
        stage_id: Optional[ID],
        content_id: Optional[ID] = None,
    ) -> Tuple[SendStreamHandle[str], Optional[Task[None]]]:
        """Start a text stream.

        Either content id or stage id must be provided.

        Args:
            stage_id: Target stage id.
            content_id: Optional pre-defined content id.

        Returns:
            Tuple[SendStreamHandle[str], Optional[Task[None]]]: A handle with send
                and end methods and the task for sending the content.
        """
        content_evt, task = self.text_content(
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

    def audio_stream(
        self,
        *,
        stage_id: Optional[ID],
        nchannels: Optional[int],
        sample_rate: Optional[int],
        sample_width: Optional[int],
        content_id: Optional[ID] = None,
    ) -> Tuple[SendStreamHandle[bytes], Optional[Task[None]]]:
        """Start a binary audio stream.

        Either content id or (stage_id, nchannels, sample_rate, sample_width) must be provided.

        Args:
            stage_id: The target stage id.
            nchannels: Number of audio channels.
            sample_rate: Audio sample rate.
            sample_width: Sample width in bytes.
            content_id: Optional pre-defined content id.

        Returns:
            Tuple[SendStreamHandle[bytes], Optional[Task[None]]]: A handle with send
                and end methods and the task for sending the content.
        """
        content_evt, task = self.audio_content(
            stage_id=stage_id,
            nchannels=nchannels,
            sample_rate=sample_rate,
            sample_width=sample_width,
            content_id=content_id,
        )
        stream_handle = self._prepare_media_stream(content_evt)
        return stream_handle, task

    def video_stream(
        self,
        *,
        stage_id: ID,
        fps: Optional[int],
        width: Optional[int],
        height: Optional[int],
        content_id: Optional[ID] = None,
    ) -> Tuple[SendStreamHandle[bytes], Optional[Task[None]]]:
        """Start a binary video stream.

        Either content id or (stage_id, fps, width, height) must be provided.

        Args:
            stage_id: The target stage id.
            fps: Video frames per second.
            width: Frame width.
            height: Frame height.
            content_id: Optional pre-defined content id.

        Returns:
            Tuple[SendStreamHandle[bytes], Optional[Task[None]]]: A handle with send
                and end methods and the task for sending the content.
        """
        content_evt, task = self.video_content(
            stage_id=stage_id,
            fps=fps,
            width=width,
            height=height,
            content_id=content_id,
        )
        stream_handle = self._prepare_media_stream(content_evt)
        return stream_handle, task

    def end_output(self) -> Tuple[OutputEnd, Optional[Task[None]]]:
        """Tell the client that the server has finished sending output."""
        self._request_state.end_output()
        self._request_state.reset()
        evt = OutputEnd()
        task = self._transport.send_event(evt)
        return evt, task

    def _prepare_media_stream(
        self,
        content: OutputContent,
    ) -> SendStreamHandle[bytes]:
        """Prepare a media stream."""

        def send(data: bytes) -> Tuple[OutputMedia, Optional[Task[None]]]:
            evt = OutputMedia(
                content_id=content.id,
                data=data,
            )
            self._request_state.media(evt)
            task = self._transport.send_bytes(evt.get_bytes())
            return evt, task

        def end() -> Tuple[Optional[OutputEnd], Optional[Task[None]]]:
            return None, None

        stream_handle = SendStreamHandle[bytes](
            content_id=content.id,
            send=send,
            end=end,
        )
        return stream_handle
