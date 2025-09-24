"""Transport subsystem.

Exports:
  - Transport, InMemoryTransport (always available)
  - WebsocketsTransport (requires `websockets` extra)
  - StarletteTransport (requires `fastapi` extra)

Optional implementations are imported lazily; attempting to access them
without installing the corresponding extras raises a helpful ImportError.
"""

from __future__ import annotations

from typing import Any

from .base import InMemoryTransport, Transport

__all__ = [
    "Transport",
    "InMemoryTransport",
]


def __getattr__(name: str) -> Any:  # pragma: no cover - simple import proxy
    if name == "WebsocketsTransport":
        try:
            from .websockets import WebsocketsTransport as _WST
        except Exception as exc:
            raise ImportError(
                "WebsocketsTransport requires the optional 'websockets' extra.\n"
                "Install with: pip install chat_api[websockets]"
            ) from exc
        return _WST
    if name == "StarletteTransport":
        try:
            from .starlette import StarletteTransport as _SLT
        except Exception as exc:
            raise ImportError(
                "StarletteTransport requires the optional 'fastapi' extra.\n"
                "Install with: pip install chat_api[fastapi]"
            ) from exc
        return _SLT
    raise AttributeError(name)
