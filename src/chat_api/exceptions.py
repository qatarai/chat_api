"""Custom exceptions for the Chat API client library."""


class ChatApiError(Exception):
    """Base exception for all Chat API errors."""


class ChatApiValidationError(ChatApiError):
    """Raised when invalid inputs or protocol usage are detected."""


class ChatApiStateError(ChatApiError):
    """Raised when operations are performed in an invalid state."""


class ChatApiTransportError(ChatApiError):
    """Raised when a transport error occurs."""
