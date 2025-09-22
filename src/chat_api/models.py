"""Pydantic models for events and binary media chunks."""

from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from .enums import ContentType, EventType, InputMode, InterruptType

# Type alias for IDs
ID = UUID
new_id = uuid4


class Event(BaseModel):
    """Base class for all event payloads."""

    event_type: EventType


# Client -> Server
class Config(Event):
    """Client->Server configuration message for a request session."""

    event_type: EventType = Field(default=EventType.CONFIG, frozen=True)
    chat_id: Optional[ID] = None
    input_mode: InputMode = Field(default=InputMode.TEXT)
    output_text: bool = Field(default=True)
    output_audio: bool = Field(default=True)
    output_video: bool = Field(default=True)
    silence_duration: float = Field(default=-1)


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


class InputInterrupt(Event):
    """Client->Server interrupt signal indicating reason for interruption."""

    event_type: EventType = Field(
        default=EventType.INPUT_INTERRUPT, frozen=True
    )
    interrupt_type: InterruptType


# Server -> Client
class OutputInitialization(Event):
    """Server->Client initialization frame with chat and request ids."""

    event_type: EventType = Field(
        default=EventType.OUTPUT_INITIALIZATION, frozen=True
    )
    chat_id: ID
    request_id: ID


class OutputStage(Event):
    """Server->Client stage descriptor in the output plan."""

    event_type: EventType = Field(default=EventType.OUTPUT_STAGE, frozen=True)
    id: ID
    parent_id: Optional[ID] = None
    title: str
    description: str


class OutputContent(Event):
    """Server->Client content declaration belonging to a stage."""

    event_type: EventType = Field(
        default=EventType.OUTPUT_CONTENT, frozen=True
    )
    id: ID
    type: ContentType
    stage_id: ID


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


class OutputEnd(Event):
    """Server->Client marker indicating the end of output for the request."""

    event_type: EventType = Field(default=EventType.OUTPUT_END, frozen=True)


class OutputMedia(Event):
    """Server->Client binary media chunk."""

    event_type: EventType = Field(default=EventType.OUTPUT_MEDIA, frozen=True)
    content_id: ID
    data: bytes

    def bytes(self) -> bytes:
        """Get the bytes of the media chunk."""
        return self.content_id.bytes + self.data
