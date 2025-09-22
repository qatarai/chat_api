"""Enumerations used throughout the Chat API library.

These enums define standardized constants for input modes, content types,
event types, and interrupt types used by the client and server components.
"""

from enum import IntEnum


class InputMode(IntEnum):
    """Supported input modes for client->server communication."""

    AUDIO = 0
    TEXT = 1


class ContentType(IntEnum):
    """Types of content produced in server->client responses."""

    AUDIO = 0
    VIDEO = 1
    TEXT = 2
    FUNCTION_CALL = 3


class EventType(IntEnum):
    """Event types exchanged between client and server."""

    CONFIG = 0
    INPUT_TEXT = 1
    INPUT_MEDIA = 2
    INPUT_END = 3
    INPUT_INTERRUPT = 4
    OUTPUT_INITIALIZATION = 5
    OUTPUT_STAGE = 6
    OUTPUT_CONTENT = 7
    OUTPUT_CONTENT_ADDITION = 8
    OUTPUT_TEXT = 9
    OUTPUT_MEDIA = 10
    OUTPUT_FUNCTION_CALL = 11
    OUTPUT_END = 12


class InterruptType(IntEnum):
    """Interrupt cause for client-originated interruptions."""

    USER = 0
    SYSTEM = 1
