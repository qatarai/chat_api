"""Process-safe handle for the server."""

from multiprocessing import Queue as ProcessQueue
from multiprocessing.shared_memory import ShareableList
from typing import Any

from ...models import (
    ID,
    Config,
    Event,
    EventRequest,
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
    StateError,
    Transcription,
)
from .base import BaseInterfaceHandle


class ServerInterfaceHandle(BaseInterfaceHandle):
    """Process-safe handle for the server."""

    def __init__(
        self,
        send_queue: "ProcessQueue[EventRequest | None]",
        shared_status: ShareableList[int],
    ) -> None:
        super().__init__(
            send_queue=send_queue,
            shared_status=shared_status,
        )

    def receive(self) -> Event:
        event = super().receive()

        if isinstance(event, Config):
            self.chat_id = event.chat_id

        return event

    def ready(
        self,
        request_id: ID,
        chat_id: ID | None = None,
    ) -> ServerReady | StateError:
        """Tell the client that the server is ready to receive input."""
        chat_id = chat_id or self.chat_id or self.new_uuid()
        event = ServerReady(chat_id=chat_id, request_id=request_id)
        return self.send(event)

    def transcription(
        self,
        transcription: Transcription,
    ) -> OutputTranscription | StateError:
        """Send audio transcription."""
        event = OutputTranscription(transcription=transcription)
        return self.send(event)

    def stage(
        self,
        title: str,
        description: str,
        stage_id: ID | None = None,
    ) -> OutputStage | StateError:
        """Send an OutputStage event."""
        stage_id = stage_id or self.new_uuid()
        event = OutputStage(id=stage_id, title=title, description=description)
        return self.send(event)

    def text_content(
        self,
        stage_id: ID,
        content_id: ID | None = None,
    ) -> OutputContent | StateError:
        """Send a text content."""
        content_id = content_id or self.new_uuid()
        event = OutputTextContent(id=content_id, stage_id=stage_id)
        return self.send(event)

    def function_call_content(
        self,
        stage_id: ID,
        content_id: ID | None = None,
    ) -> OutputContent | StateError:
        """Send a function call content."""
        content_id = content_id or self.new_uuid()
        event = OutputFunctionCallContent(id=content_id, stage_id=stage_id)
        return self.send(event)

    def audio_content(
        self,
        stage_id: ID,
        nchannels: int,
        sample_rate: int,
        sample_width: int,
        content_id: ID | None = None,
    ) -> OutputContent | StateError:
        """Send an audio content."""
        content_id = content_id or self.new_uuid()
        event = OutputAudioContent(
            id=content_id,
            stage_id=stage_id,
            nchannels=nchannels,
            sample_rate=sample_rate,
            sample_width=sample_width,
        )
        return self.send(event)

    def video_content(
        self,
        stage_id: ID,
        fps: int,
        width: int,
        height: int,
        content_id: ID | None = None,
    ) -> OutputContent | StateError:
        """Send a video content."""
        content_id = content_id or self.new_uuid()
        event = OutputVideoContent(
            id=content_id,
            stage_id=stage_id,
            fps=fps,
            width=width,
            height=height,
        )
        return self.send(event)

    def content_addition(
        self,
        content_id: ID,
        metadata: dict[str, Any],
    ) -> OutputContentAddition | StateError:
        """Send an OutputContentAddition for an existing content item."""
        event = OutputContentAddition(content_id=content_id, metadata=metadata)
        return self.send(event)

    def function_call(
        self,
        content_id: ID,
        data: str,
    ) -> OutputFunctionCall | StateError:
        """Send a function call."""
        event = OutputFunctionCall(content_id=content_id, data=data)
        return self.send(event)

    def text(
        self,
        content_id: ID,
        data: str,
    ) -> OutputText | StateError:
        """Send a text."""
        event = OutputText(content_id=content_id, data=data)
        return self.send(event)

    def audio(
        self,
        content_id: ID,
        data: bytes,
    ) -> OutputMedia | StateError:
        """Send a binary audio."""
        event = OutputMedia(content_id=content_id, data=data)
        return self.send(event)

    def video(
        self,
        content_id: ID,
        data: bytes,
    ) -> OutputMedia | StateError:
        """Send a binary video."""
        event = OutputMedia(content_id=content_id, data=data)
        return self.send(event)

    def end_output(self) -> OutputEnd | StateError:
        """Tell the client that the server has finished sending output."""
        event = OutputEnd()
        return self.send(event)
