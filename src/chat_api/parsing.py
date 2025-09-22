"""Parsing helpers for events and binary media chunks."""

from __future__ import annotations

import json
from typing import Type
from uuid import UUID

from .enums import EventType
from .models import (
    Config,
    Event,
    InputEnd,
    InputInterrupt,
    InputMedia,
    InputText,
    OutputContent,
    OutputContentAddition,
    OutputEnd,
    OutputFunctionCall,
    OutputInitialization,
    OutputMedia,
    OutputStage,
    OutputText,
)

_EVENT_CLASS_BY_TYPE: dict[int, Type[Event]] = {
    EventType.CONFIG: Config,
    EventType.INPUT_END: InputEnd,
    EventType.INPUT_INTERRUPT: InputInterrupt,
    EventType.INPUT_MEDIA: InputMedia,
    EventType.INPUT_TEXT: InputText,
    EventType.OUTPUT_CONTENT: OutputContent,
    EventType.OUTPUT_CONTENT_ADDITION: OutputContentAddition,
    EventType.OUTPUT_END: OutputEnd,
    EventType.OUTPUT_FUNCTION_CALL: OutputFunctionCall,
    EventType.OUTPUT_INITIALIZATION: OutputInitialization,
    EventType.OUTPUT_STAGE: OutputStage,
    EventType.OUTPUT_TEXT: OutputText,
}


def parse_text_event(text: str) -> Event:
    """Parse a JSON text event into a typed model.

    Args:
        text: The raw JSON string.

    Returns:
        Event: The parsed pydantic event instance.

    Raises:
        ValueError: If the payload is missing event_type or is unknown.
    """
    payload = json.loads(text)
    event_type = payload.get("event_type")

    if event_type is None:
        raise ValueError("Missing event_type in text payload")

    cls = _EVENT_CLASS_BY_TYPE.get(int(event_type))

    if cls is None:
        raise ValueError(f"Unknown event_type: {event_type}")

    return cls.model_validate(payload)


def parse_bytes_event(
    blob: bytes,
    is_input: bool,
) -> InputMedia | OutputMedia:
    """Parse a bytes event into a typed model.

    This is used for both client->server and server->client communication.

    Extracting the uuid prefix is left to the caller.

    Args:
        blob: The raw bytes.

    Returns:
        InputMedia | OutputMedia: A parsed media chunk with fields populated.

    Raises:
        ValueError: If the event is empty.
    """
    if len(blob) == 0:
        raise ValueError("Event must not be empty")

    return (
        InputMedia(data=blob)
        if is_input
        else OutputMedia(
            content_id=UUID(bytes=blob[:16]),
            data=blob[16:],
        )
    )
