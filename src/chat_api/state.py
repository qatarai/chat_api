"""State helpers for tracking request initialization, stages, and contents."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Set
from uuid import UUID

from .enums import ContentType, InputMode
from .models import (
    Config,
    InputInterrupt,
    OutputContent,
    OutputContentAddition,
    OutputStage,
)


@dataclass
class RequestState:
    """Mutable request-scoped state used by clients.

    Attributes:
        config: The request configuration.
        request_id: The active request id once initialized.
        initialized: Whether the request has been initialized.
        stages: Map of stage id to stage.
        contents: Map of content id to content.
        content_streaming_open: Set of content ids with open media streams.
        content_associated: Set of content ids that have been associated with data.
        input_ended: Whether the input has been ended.
        output_ended: Whether the output has been ended.
        input_interrupt: The interrupt reason if the request was interrupted.
    """

    config: Optional[Config] = None
    request_id: Optional[UUID] = None
    initialized: bool = False
    stages: Dict[UUID, OutputStage] = field(default_factory=dict)
    contents: Dict[UUID, OutputContent] = field(default_factory=dict)
    content_streaming_open: Set[UUID] = field(default_factory=set)
    content_associated: Set[UUID] = field(default_factory=set)
    input_ended: bool = False
    output_ended: bool = False
    input_interrupt: Optional[InputInterrupt] = None

    #######################################################
    # State Consistency
    # ----------------------------------------------------
    # Ensure the request is in a valid state via assertions
    #######################################################

    def assert_not_interrupted(self) -> None:
        """Raise if the request has been interrupted."""
        if self.input_interrupt is not None:
            raise ValueError("Request has been interrupted")

    def assert_initialized(self) -> None:
        """Raise if the request has not been initialized.

        This is used to ensure that the request is initialized before
        performing certain actions.

        Raises:
            ValueError: If not initialized.
        """
        if not self.initialized:
            raise ValueError("Request not initialized")

    def assert_not_initialized(self) -> None:
        """Raise if the request has already been initialized.

        This is used to ensure that the request is not initialized before
        performing certain actions.

        Raises:
            ValueError: If already initialized.
        """
        if self.initialized:
            raise ValueError("Request already initialized")

    def assert_ready_to_end_input(self) -> None:
        """Raise if the request is not ready to end the input.

        This is used to ensure that the request is ready to end the input.
        """
        self.assert_initialized()

        if self.input_ended:
            raise ValueError("Input has already been ended")

    def assert_ready_to_output(self) -> None:
        """Raise if the request is not ready to output.

        This is used to ensure that the request is ready to output before
        performing certain actions.
        """
        self.assert_initialized()

        if (
            not self.input_ended
            and self.config
            and self.config.input_mode != InputMode.TEXT
        ):
            raise ValueError("Input has not been ended and is not text")

        if self.output_ended:
            raise ValueError("Output has already been ended")

    def assert_ready_to_end_output(self) -> None:
        """Raise if the request is not ready to end the output.

        This is used to ensure that the request is ready to end the output.
        """
        self.assert_ready_to_output()

        if self.content_streaming_open:
            raise ValueError(
                f"`Content`s with ids {self.content_streaming_open} have open streams"
            )

        if not self.content_associated:
            raise ValueError(
                f"`Content`s with ids {self.content_associated} have not been associated with data"
            )

    def assert_content_not_associated(
        self,
        content_id: UUID,
    ) -> None:
        """Raise if the given content id has been associated with data."""
        self.assert_ready_to_output()

        if content_id in self.content_associated:
            raise ValueError(
                f"Data has already been associated with content {content_id}"
            )

    #######################################################
    # State Mutations
    # ----------------------------------------------------
    # Mutate the request state via methods
    #######################################################

    def initialize(
        self,
        config: Config,
        request_id: UUID,
    ) -> None:
        """Initialize the request.

        Args:
            config: The request configuration.
            request_id: The request id to set.
        """
        self.assert_not_interrupted()
        self.assert_not_initialized()

        self.config = config
        self.request_id = request_id
        self.initialized = True

    def end_input(self) -> None:
        """End the input.

        Raises:
            ValueError: If the input has already been ended.
        """
        self.assert_not_interrupted()
        self.assert_initialized()

        self.input_ended = True

    def add_stage(
        self,
        stage: OutputStage,
    ) -> None:
        """Register a new stage.

        Args:
            stage: The stage to add.

        Raises:
            ValueError: If id duplicates or parent not found.
        """
        self.assert_not_interrupted()
        self.assert_ready_to_output()

        # Check for duplicate stages
        if stage.id in self.stages:
            raise ValueError(f"Duplicate stage id: {stage.id}")

        # Check for missing parent
        if stage.parent_id and stage.parent_id not in self.stages:
            raise ValueError(
                f"Parent stage {stage.parent_id} not found for stage {stage.id}"
            )

        # Detect circular parent-child relationships
        visited: Set[UUID] = set()
        current = stage.parent_id
        while current is not None:
            if current in visited:
                raise ValueError(
                    f"Circular stage relationship detected involving {current}"
                )
            visited.add(current)
            current = self.stages[current].parent_id

        self.stages[stage.id] = stage

    def add_content(
        self,
        content: OutputContent,
    ) -> None:
        """Register content under a stage.

        Args:
            content: The content to add.

        Raises:
            ValueError: If content id duplicates or stage missing.
        """
        self.assert_not_interrupted()
        self.assert_ready_to_output()

        # Check for duplicate contents
        if content.id in self.contents:
            raise ValueError(f"Duplicate content id: {content.id}")

        # Check for missing stage
        if content.stage_id not in self.stages:
            raise ValueError(
                f"Stage {content.stage_id} not found for content {content.id}"
            )

        self.contents[content.id] = content

    def has_content(
        self,
        content_id: UUID,
    ) -> bool:
        """Return True if the given content id is registered."""
        self.assert_not_interrupted()
        self.assert_ready_to_output()

        return content_id in self.contents

    def add_content_addition(
        self,
        content_addition: OutputContentAddition,
    ) -> None:
        """Validate that a content addition references known content.

        Args:
            content_addition: The content addition.

        Raises:
            ValueError: If the content id is unknown.
        """
        # Check for missing content
        if not self.has_content(content_addition.content_id):
            raise ValueError(
                f"Unknown content id for addition: {content_addition.content_id}"
            )

    def add_function_call(
        self,
        content_id: UUID,
    ) -> None:
        """Validate the content id is known and not associated with data."""
        self.assert_not_interrupted()
        self.assert_ready_to_output()

        # Check for missing content
        if not self.has_content(content_id):
            raise ValueError(
                f"Unknown content id for function call: {content_id}"
            )

        # Check for content already associated with data
        self.assert_content_not_associated(content_id)

        # Add the content to the set of associated content
        self.content_associated.add(content_id)

    def is_stream_open(
        self,
        content_id: UUID,
    ) -> bool:
        """Return True if the given content id has an open stream."""
        self.assert_ready_to_output()

        return content_id in self.content_streaming_open

    def open_stream(
        self,
        content_id: UUID,
    ) -> None:
        """Mark a media stream as open for the given content id.

        Raises:
            ValueError: If a stream is already open.
        """
        self.assert_not_interrupted()
        self.assert_ready_to_output()
        self.assert_content_not_associated(content_id)

        if content_id in self.content_streaming_open:
            raise ValueError(f"Stream already open for content {content_id}")

        # Check stream is supported
        if self.contents[content_id].type == ContentType.FUNCTION_CALL:
            raise ValueError(
                f"FunctionCall does not support streaming: {content_id}"
            )

        self.content_streaming_open.add(content_id)
        self.content_associated.add(content_id)

    def close_stream(
        self,
        content_id: UUID,
    ) -> None:
        """Mark a media stream as closed for the given content id.

        Raises:
            ValueError: If a stream is not currently open.
        """
        self.assert_not_interrupted()
        self.assert_ready_to_output()

        if content_id not in self.content_streaming_open:
            raise ValueError(f"Stream not open for content {content_id}")

        self.content_streaming_open.remove(content_id)

    def end_output(self) -> None:
        """Mark the output as ended."""
        self.assert_not_interrupted()
        self.assert_ready_to_end_output()

        self.output_ended = True

    def interrupt(self, interrupt: InputInterrupt) -> None:
        """Mark the request as interrupted."""
        self.assert_not_interrupted()

        self.input_interrupt = interrupt
