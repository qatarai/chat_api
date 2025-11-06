"""Pydantic models for events and binary media chunks."""

from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .enums import ContentType, EventType, InputMode, InterruptType

########################################################
# Type aliases
########################################################

ID = UUID
new_id = uuid4


########################################################
# Events
########################################################


class Event(BaseModel):
    """Base class for all event payloads."""

    event_type: EventType


# Client -> Server
class Config(Event):
    """Client->Server configuration message for a request session."""

    event_type: EventType = Field(default=EventType.CONFIG, frozen=True)
    chat_id: Optional[ID] = None
    # Input
    input_mode: InputMode = Field(default=InputMode.TEXT)
    silence_duration: float = Field(default=-1)
    nchannels: int = Field(default=1)
    sample_rate: int = Field(default=16000)
    sample_width: int = Field(default=2)
    # Output
    output_text: bool = Field(default=True)
    output_audio: bool = Field(default=True)
    output_video: bool = Field(default=True)


class InputText(Event):
    """Client->Server input text chunk."""

    event_type: EventType = Field(default=EventType.INPUT_TEXT, frozen=True)
    data: str


class InputMedia(Event):
    """Client->Server binary media chunk."""

    event_type: EventType = Field(default=EventType.INPUT_MEDIA, frozen=True)
    data: bytes


class InputEnd(Event):
    """Client->Server marker indicating end of input."""

    event_type: EventType = Field(default=EventType.INPUT_END, frozen=True)


class Interrupt(Event):
    """Client->Server interrupt signal indicating reason for interruption."""

    event_type: EventType = Field(default=EventType.INTERRUPT, frozen=True)
    interrupt_type: InterruptType


# Server -> Client
class ServerReady(Event):
    """Server->Client ready signal indicating the server is ready to receive events.

    This is sent after the server has received the client's configuration and
    is ready to start processing the request.
    """

    event_type: EventType = Field(default=EventType.SERVER_READY, frozen=True)
    chat_id: ID
    request_id: ID


class OutputTranscription(Event):
    """Server->Client audio transcription."""

    event_type: EventType = Field(
        default=EventType.OUTPUT_TRANSCRIPTION, frozen=True
    )
    transcription: Transcription


class OutputStage(Event):
    """Server->Client stage descriptor in the output plan."""

    event_type: EventType = Field(default=EventType.OUTPUT_STAGE, frozen=True)
    id: ID
    parent_id: Optional[ID] = None
    title: str
    description: str


class OutputContent(Event):
    """Server->Client content declaration belonging to a stage."""

    id: ID
    type: ContentType
    stage_id: ID


class OutputTextContent(OutputContent):
    """Server->Client text content declaration belonging to a stage."""

    event_type: EventType = Field(
        default=EventType.OUTPUT_TEXT_CONTENT, frozen=True
    )
    type: ContentType = Field(default=ContentType.TEXT, frozen=True)


class OutputFunctionCallContent(OutputContent):
    """Server->Client function call content declaration belonging to a stage."""

    event_type: EventType = Field(
        default=EventType.OUTPUT_FUNCTION_CALL_CONTENT, frozen=True
    )
    type: ContentType = Field(default=ContentType.FUNCTION_CALL, frozen=True)


class OutputAudioContent(OutputContent):
    """Server->Client audio content declaration belonging to a stage."""

    event_type: EventType = Field(
        default=EventType.OUTPUT_AUDIO_CONTENT, frozen=True
    )
    type: ContentType = Field(default=ContentType.AUDIO, frozen=True)
    nchannels: int
    sample_rate: int
    sample_width: int


class OutputVideoContent(OutputContent):
    """Server->Client video content declaration belonging to a stage."""

    event_type: EventType = Field(
        default=EventType.OUTPUT_VIDEO_CONTENT, frozen=True
    )
    type: ContentType = Field(default=ContentType.VIDEO, frozen=True)
    fps: int
    width: int
    height: int


class OutputContentAddition(Event):
    """Server->Client additional metadata for an existing content item."""

    event_type: EventType = Field(
        default=EventType.OUTPUT_CONTENT_ADDITION, frozen=True
    )
    content_id: ID
    metadata: Dict[str, Any] = Field(default_factory=dict)


class OutputText(Event):
    """Server->Client text chunk associated with the current content."""

    event_type: EventType = Field(default=EventType.OUTPUT_TEXT, frozen=True)
    content_id: ID
    data: str


class OutputFunctionCall(Event):
    """Server->Client function call payload encoded as a JSON string."""

    event_type: EventType = Field(
        default=EventType.OUTPUT_FUNCTION_CALL, frozen=True
    )
    content_id: ID
    data: str


class OutputMedia(Event):
    """Server->Client binary media chunk."""

    event_type: EventType = Field(default=EventType.OUTPUT_MEDIA, frozen=True)
    content_id: ID
    data: bytes

    def get_bytes(self) -> bytes:
        """Get the bytes of the media chunk."""
        return self.content_id.bytes + self.data


class OutputEnd(Event):
    """Server->Client marker indicating the end of output for the request."""

    event_type: EventType = Field(default=EventType.OUTPUT_END, frozen=True)


class SessionEnd(Event):
    """Server->Client marker indicating the end of the session."""

    event_type: EventType = Field(default=EventType.SESSION_END, frozen=True)


########################################################
# Speech transcription
########################################################


class Word(BaseModel):
    """A word in a speech.

    Attributes:
        text : str or None, default=None
            The text of the word.
        start : float or None, default=None
            Start time of the word in seconds.
        end : float or None, default=None
            End time of the word in seconds.
        speaker : str or None, default=None
            Speaker identifier for the segment.
        score : float or None, default=None
            Confidence score of the word.
    """

    text: str | None = None
    start: float | None = None
    end: float | None = None
    speaker: str | None = None
    score: float | None = None


class Segment(Word):
    """A segment of a speech.

    Attributes:
        words : list[Word] or None, default=None
            List of words in the segment.
    """

    words: list[Word] | None = None


class Transcription(BaseModel):
    """A list of segments of a speech.

    Contains the transcription of the speech, including segments and optional
    speaker embeddings.

    Attributes:
        segments : list[Segment]
            List of transcribed segments.
        language : str or None, default=None
            Detected or specified language of the transcription.
        speaker_embeddings : dict[str, list[float]] or None, default=None
            Speaker embeddings for each speaker ID.
    """

    segments: list[Segment]
    language: str | None = None
    speaker_embeddings: dict[str, list[float]] | None = None
