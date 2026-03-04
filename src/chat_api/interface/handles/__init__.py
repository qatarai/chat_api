"""Process-safe handles for the interface."""

from .base import BaseInterfaceHandle
from .client import ClientInterfaceHandle
from .server import ServerInterfaceHandle

__all__ = [
    "BaseInterfaceHandle",
    "ClientInterfaceHandle",
    "ServerInterfaceHandle",
]
