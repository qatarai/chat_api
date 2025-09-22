"""Shared logic for Chat API clients (sync and async).

Provides state management, validation, and event-building helpers that do not
perform any I/O. Concrete clients are responsible only for sending the prepared
payloads over their respective transports.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..enums import ContentType
from ..models import (
    ID,
    OutputContent,
    OutputContentAddition,
    OutputFunctionCall,
    OutputInitialization,
    OutputMedia,
    OutputStage,
    OutputText,
    new_id,
)
from ..state import RequestState


class _ServerToClientShared:
    """Shared logic for clients.

    Holds request state and common helpers.
    """

    def __init__(self) -> None:
        """Initialize shared client state.

        Sets up a fresh `RequestState` instance and an internal mapping from
        output `content_id` values to 16-byte UUIDs used for media stream
        chunk identifiers.
        """
        self._state = RequestState()

    #######################################################
    # ID helpers
    # ----------------------------------------------------
    # Generate new UUIDs
    #######################################################
    @staticmethod
    def _new_uuid() -> ID:
        """Generate a random ID.

        Returns:
            ID: A new RFC 4122 random ID.
        """
        return new_id()

    #######################################################
    # Event builders (no I/O)
    #######################################################
    def _get_output_content_state(
        self,
        *,
        content_id: Optional[ID],
        content_type: ContentType,
        stage_id: ID,
    ) -> tuple[OutputContent, bool]:
        """Get the state of a content for the given ids.

        If a `content_id` is provided and already registered, returns a no-op
        marker (OutputContent for reference only) and the same id with
        `created=False` so call sites can skip re-sending. If not registered,
        it will be prepared and returned with `created=True` so call sites can
        send the resulting event.

        This centralizes the rule: any output data must be associated with a
        content that has already been sent; if not, content must be created
        before the data is sent.

        Returns:
            tuple[OutputContent, bool]: The prepared event, and a boolean indicating if the content should be sent.
            and a boolean indicating if the content should be sent.
        """
        if content_id and self._state.has_content(content_id):
            # Return a marker event for consistency; callers should not resend.
            return (
                OutputContent(
                    id=content_id,
                    type=content_type,
                    stage_id=stage_id,
                ),
                False,
            )

        # Not present; prepare a new OutputContent
        return (
            self._prepare_output_content(
                content_type=content_type,
                stage_id=stage_id,
                content_id=content_id,
            ),
            True,
        )

    def _prepare_output_initialization(
        self,
        *,
        chat_id: Optional[ID],
        request_id: Optional[ID],
    ) -> OutputInitialization:
        """Build OutputInitialization and update state.

        Returns:
            OutputInitialization: The event ready to be sent.
        """
        chat_id = chat_id or self._new_uuid()
        request_id = request_id or self._new_uuid()

        return OutputInitialization(
            chat_id=chat_id,
            request_id=request_id,
        )

    def _prepare_output_stage(
        self,
        *,
        title: str,
        description: str,
        stage_id: Optional[ID],
        parent_id: Optional[ID],
    ) -> OutputStage:
        """Build an `OutputStage` event and register the stage in state.

        Args:
            title: Human-readable stage title.
            description: Optional description of the stage purpose.
            stage_id: Optional explicit id to use; generates one if not provided.
            parent_id: Optional id of the parent stage to nest under.

        Returns:
            OutputStage: The prepared event.

        Raises:
            ChatApiStateError: If the request has not been initialized.
            ValueError: If the provided ids violate state constraints (duplicate
                stage id or unknown parent id).
        """
        stage_id = stage_id or self._new_uuid()

        return OutputStage(
            id=stage_id,
            parent_id=parent_id,
            title=title,
            description=description,
        )

    def _prepare_output_content(
        self,
        *,
        content_type: ContentType,
        stage_id: ID,
        content_id: Optional[ID],
    ) -> OutputContent:
        """Build an `OutputContent` event and register the content in state.

        Args:
            content_type: The type of content being produced.
            stage_id: The id of the stage to attach this content to.
            content_id: Optional explicit id to use; generates one if omitted.

        Returns:
            OutputContent: The prepared event.

        Raises:
            ChatApiStateError: If the request has not been initialized.
            ValueError: If the content id duplicates an existing one or the
                `stage_id` does not exist.
        """
        content_id = content_id or self._new_uuid()

        return OutputContent(
            id=content_id,
            type=content_type,
            stage_id=stage_id,
        )

    def _prepare_output_content_addition(
        self,
        *,
        content_id: ID,
        metadata: Optional[Dict[str, Any]],
    ) -> OutputContentAddition:
        """Build an `OutputContentAddition` event for an existing content item.

        Args:
            content_id: The id of the content being augmented.
            metadata: Optional metadata to include with the addition.

        Returns:
            OutputContentAddition: The event ready to be sent.

        Raises:
            ChatApiStateError: If the request has not been initialized.
            ValueError: If the `content_id` is not known in the current state.
        """
        return OutputContentAddition(
            content_id=content_id,
            metadata=metadata or {},
        )

    def _prepare_output_text(
        self,
        *,
        content_id: ID,
        data: str,
    ) -> OutputText:
        """Build an `OutputText` event for the given content id.

        Args:
            content_id: The id of the content to which this text belongs.
            data: The text payload.

        Returns:
            OutputText: The event ready to be sent.

        Raises:
            ChatApiStateError: If the request has not been initialized.
        """
        return OutputText(
            content_id=content_id,
            data=data,
        )

    def _prepare_output_media(
        self,
        *,
        content_id: ID,
        data: bytes,
    ) -> OutputMedia:
        """Build an `OutputMedia` event for the given content id.

        Args:
            content_id: The id of the content to which this media belongs.
            data: The media payload.

        Returns:
            OutputMedia: The event ready to be sent.
        """
        return OutputMedia(
            content_id=content_id,
            data=data,
        )

    def _prepare_output_function_call(
        self,
        *,
        content_id: ID,
        json_data: str,
    ) -> OutputFunctionCall:
        """Build a function call output event dictionary.

        Args:
            content_id: The id of the content representing the function call.
            json_data: The JSON-serialized call payload.

        Returns:
            OutputFunctionCall: The event ready to be sent.
            serialized payload, suitable for transport.

        Raises:
            ChatApiStateError: If the request has not been initialized.
        """
        return OutputFunctionCall(
            content_id=content_id,
            data=json_data,
        )
