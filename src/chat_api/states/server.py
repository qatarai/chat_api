"""State for tracking and validating server request state."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Set

from ..enums import InputMode
from ..exceptions import ChatApiStateError
from ..models import (
    ID,
    OutputContent,
    OutputContentAddition,
    OutputFunctionCall,
    OutputMedia,
    OutputStage,
    OutputText,
)
from .base import RequestState


@dataclass
class ServerRequestState(RequestState):
    """Mutable request-scoped state used by server."""

    _stage_id_to_parent_id: Dict[ID, Optional[ID]] = field(
        default_factory=dict, init=False
    )
    _content_id_to_stage_id: Dict[ID, ID] = field(
        default_factory=dict, init=False
    )
    _content_ids_with_data: Set[ID] = field(default_factory=set, init=False)
    _output_end: bool = field(default=False, init=False)

    def transcription(self) -> None:
        """Validate possibility of sending a transcription."""
        if self._interrupt:
            raise ChatApiStateError("Request has been interrupted")

        if not self._ready:
            raise ChatApiStateError("Server is not ready")

        if self._config and self._config.input_mode != InputMode.AUDIO:
            raise ChatApiStateError("Input mode is not audio")

        if self._output_end:
            raise ChatApiStateError("Output has already been ended")

    def stage(self, stage: OutputStage) -> None:
        """Validate possibility of sending a stage."""
        if self._interrupt:
            raise ChatApiStateError("Request has been interrupted")

        if not self._input_end:
            raise ChatApiStateError("Input has not been ended")

        if self._output_end:
            raise ChatApiStateError("Output has already been ended")

        if stage.id in self._stage_id_to_parent_id:
            raise ChatApiStateError(
                "Stage with id {stage.id} already sent. "
                "Stages must have unique ids."
            )

        # Check for parent-child cycles
        visited: Set[ID] = set()
        current = stage.parent_id
        while current is not None:
            if current in visited:
                raise ChatApiStateError(
                    f"Circular stage relationship detected involving "
                    f"{current} and {stage.id}"
                )
            visited.add(current)
            current = self._stage_id_to_parent_id[current]

        self._stage_id_to_parent_id[stage.id] = stage.parent_id

    def has_content(self, content: OutputContent) -> bool:
        """Check if the content has been sent."""
        return content.id in self._content_id_to_stage_id

    def content(self, content: OutputContent) -> None:
        """Validate possibility of sending content."""
        if self._interrupt:
            raise ChatApiStateError("Request has been interrupted")

        if not self._input_end:
            raise ChatApiStateError("Input has not been ended")

        if self._output_end:
            raise ChatApiStateError("Output has already been ended")

        if content.id in self._content_id_to_stage_id:
            raise ChatApiStateError(
                "Content with id {content.id} already sent. "
                "Contents must have unique ids."
            )

        self._content_id_to_stage_id[content.id] = content.stage_id

    def content_addition(
        self,
        content_addition: OutputContentAddition,
    ) -> None:
        """Validate possibility of sending content addition."""
        if self._interrupt:
            raise ChatApiStateError("Request has been interrupted")

        if not self._input_end:
            raise ChatApiStateError("Input has not been ended")

        if self._output_end:
            raise ChatApiStateError("Output has already been ended")

        if content_addition.content_id not in self._content_id_to_stage_id:
            raise ChatApiStateError(
                "Content with id {content_addition.content_id} not found. "
                "Content must be sent before adding metadata."
            )

    def function_call(self, function_call: OutputFunctionCall) -> None:
        """Validate possibility of sending function call."""
        if self._interrupt:
            raise ChatApiStateError("Request has been interrupted")

        if not self._input_end:
            raise ChatApiStateError("Input has not been ended")

        if self._output_end:
            raise ChatApiStateError("Output has already been ended")

        if function_call.content_id not in self._content_id_to_stage_id:
            raise ChatApiStateError(
                "Content with id {function_call.content_id} not found. "
                "Content must be sent before sending function call."
            )

        if function_call.content_id in self._content_ids_with_data:
            raise ChatApiStateError(
                "Content with id {function_call.content_id} already has data. "
                "Each content can only have one data associated with it."
            )

        self._content_ids_with_data.add(function_call.content_id)

    def text(self, text: OutputText) -> None:
        """Validate possibility of sending text."""
        if self._interrupt:
            raise ChatApiStateError("Request has been interrupted")

        if not self._input_end:
            raise ChatApiStateError("Input has not been ended")

        if self._output_end:
            raise ChatApiStateError("Output has already been ended")

        if text.content_id not in self._content_id_to_stage_id:
            raise ChatApiStateError(
                "Content with id {text.content_id} not found. "
                "Content must be sent before sending text."
            )

        self._content_ids_with_data.add(text.content_id)

    def media(self, media: OutputMedia) -> None:
        """Validate possibility of sending media."""
        if self._interrupt:
            raise ChatApiStateError("Request has been interrupted")

        if not self._input_end:
            raise ChatApiStateError("Input has not been ended")

        if self._output_end:
            raise ChatApiStateError("Output has already been ended")

        if media.content_id not in self._content_id_to_stage_id:
            raise ChatApiStateError(
                "Content with id {media.content_id} not found. "
                "Content must be sent before sending media."
            )

        self._content_ids_with_data.add(media.content_id)

    def end(self) -> None:
        """Validate possibility of sending end."""
        if self._interrupt:
            raise ChatApiStateError("Request has been interrupted")

        if not self._input_end:
            raise ChatApiStateError("Input has not been ended")

        if self._output_end:
            raise ChatApiStateError("Output has already been ended")

        if len(self._content_ids_with_data) != len(
            self._content_id_to_stage_id
        ):
            raise ChatApiStateError(
                "All content must have data before sending end."
            )

        self._output_end = True
