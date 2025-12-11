"""Custom exceptions for the Chat API client library."""


class ChatApiException(Exception):
    """Base exception for all Chat API errors."""


class ChatApiStateException(ChatApiException):
    """Raised when operations are performed in an invalid state."""


class ChatApiTransportException(ChatApiException):
    """Raised when a transport error occurs."""
