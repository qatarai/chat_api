"""State for tracking and validating client request state."""

from __future__ import annotations

from dataclasses import dataclass, field

from chat_api.enums import InputMode
from chat_api.exceptions import ChatApiStateError

from .base import RequestState


@dataclass
class ClientRequestState(RequestState):
    """Mutable request-scoped state used by client."""

    _text: bool = field(default=False, init=False)

    def text(self) -> None:
        """Validate possibility of sending text."""
        if self._interrupt:
            raise ChatApiStateError("Request has been interrupted")

        if not self._ready:
            raise ChatApiStateError("Server is not ready")

        if self._input_end:
            raise ChatApiStateError("Input has already been ended")

        if self._config and self._config.input_mode != InputMode.TEXT:
            raise ChatApiStateError("Input mode is not text")

        if self._text:
            raise ChatApiStateError(
                "Text already sent. Only one text can be sent as input."
            )

        self._text = True

    def media(self) -> None:
        """Validate possibility of sending media."""
        if self._interrupt:
            raise ChatApiStateError("Request has been interrupted")

        if not self._ready:
            raise ChatApiStateError("Server is not ready")

        if self._input_end:
            raise ChatApiStateError("Input has already been ended")

        if self._config and self._config.input_mode != InputMode.AUDIO:
            raise ChatApiStateError("Input mode is not audio")

    def reset(self) -> None:
        super().reset()
        self._text = False
