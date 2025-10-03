"""Base state for tracking and validating request state."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from chat_api.models import Config

from ..exceptions import ChatApiStateError


@dataclass
class RequestState(ABC):
    """Base request state.

    Validates the state of the request.

    Raises:
        ChatApiStateError: If the request is not in a valid state.
    """

    _config: Optional[Config] = field(default=None, init=False)
    _ready: bool = field(default=False, init=False)
    _input_end: bool = field(default=False, init=False)
    _interrupt: bool = field(default=False, init=False)

    def ready(self, config: Config) -> None:
        """Mark the server as ready to receive input."""
        if self._interrupt:
            raise ChatApiStateError("Request has been interrupted")

        if self._ready:
            raise ChatApiStateError("Server already ready")

        self._config = config
        self._ready = True

    def end_input(self) -> None:
        """End the input."""
        if self._interrupt:
            raise ChatApiStateError("Request has been interrupted")

        if not self._ready:
            raise ChatApiStateError("Server is not ready")

        if self._input_end:
            raise ChatApiStateError("Input has already been ended")

        self._input_end = True

    def interrupt(self) -> None:
        """Interrupt the request."""
        if self._interrupt:
            raise ChatApiStateError("Request has already been interrupted")

        self._interrupt = True
