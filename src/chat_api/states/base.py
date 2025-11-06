"""Base state for tracking and validating request state."""

from __future__ import annotations

from abc import ABC
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
    _output_end: bool = field(default=False, init=False)
    _session_end: bool = field(default=False, init=False)

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

    def end_output(self) -> None:
        """Validate possibility of ending the output."""
        if self._interrupt:
            raise ChatApiStateError("Request has been interrupted")

        if not self._input_end:
            raise ChatApiStateError("Input has not been ended")

        if self._output_end:
            raise ChatApiStateError("Output has already been ended")

        self._output_end = True

    def end_session(self) -> None:
        """End the session."""
        if self._session_end:
            raise ChatApiStateError("Session has already been ended")

        self._session_end = True

    def reset(self) -> None:
        """Reset the request state.

        This is not a full reset; it delineates the state of the request for
        the next input from the same client/session.
        """
        if self._session_end:
            raise ChatApiStateError("Session has already been ended")

        self._input_end = False
        self._interrupt = False
        self._output_end = False
