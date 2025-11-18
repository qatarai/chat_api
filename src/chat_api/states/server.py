"""State for tracking and validating server request state."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Set

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

    _stage_id_to_stage: Dict[ID, OutputStage] = field(
        default_factory=dict, init=False
    )
    _content_id_to_content: Dict[ID, OutputContent] = field(
        default_factory=dict, init=False
    )
    _content_ids_with_data: Set[ID] = field(default_factory=set, init=False)

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

        if stage.id in self._stage_id_to_stage:
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
            current = self._stage_id_to_stage[current].parent_id

        self._stage_id_to_stage[stage.id] = stage

    def has_content(self, content: OutputContent | ID) -> OutputContent | None:
        """Check if the content has been sent and return it if it has."""
        if isinstance(content, OutputContent):
            content_id = content.id
        else:
            content_id = content

        return self._content_id_to_content.get(content_id)

    def content(self, content: OutputContent) -> None:
        """Validate possibility of sending content."""
        if self._interrupt:
            raise ChatApiStateError("Request has been interrupted")

        if not self._input_end:
            raise ChatApiStateError("Input has not been ended")

        if self._output_end:
            raise ChatApiStateError("Output has already been ended")

        if self.has_content(content):
            raise ChatApiStateError(
                "Content with id {content.id} already sent. "
                "Contents must have unique ids."
            )

        self._content_id_to_content[content.id] = content

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

        if not self.has_content(content_addition.content_id):
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

        if not self.has_content(function_call.content_id):
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

        if not self.has_content(text.content_id):
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

        if not self.has_content(media.content_id):
            raise ChatApiStateError(
                "Content with id {media.content_id} not found. "
                "Content must be sent before sending media."
            )

        self._content_ids_with_data.add(media.content_id)

    def end_output(self) -> None:
        """Validate possibility of ending the output."""
        super().end_output()

        try:
            if len(self._content_ids_with_data) != len(
                self._content_id_to_content
            ):
                raise ChatApiStateError(
                    "All content must have data before ending the output."
                )
        except ChatApiStateError as e:
            self._output_end = False
            raise e

    def interrupt(self) -> None:
        super().interrupt()
        self._stage_id_to_stage.clear()
        self._content_id_to_content.clear()
        self._content_ids_with_data.clear()

    def reset(self) -> None:
        super().reset()
        self._stage_id_to_stage.clear()
        self._content_id_to_content.clear()
        self._content_ids_with_data.clear()
        self._output_end = False
