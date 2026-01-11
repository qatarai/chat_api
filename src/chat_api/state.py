"""Track and validate events."""

from dataclasses import dataclass, field

from .enums import ContentType, InputMode, Status
from .exceptions import ChatApiStateException
from .models import (
    ID,
    Config,
    Error,
    Event,
    InputEnd,
    InputMedia,
    InputText,
    Interrupt,
    OutputAudioContent,
    OutputContent,
    OutputContentAddition,
    OutputEnd,
    OutputFunctionCall,
    OutputFunctionCallContent,
    OutputMedia,
    OutputStage,
    OutputText,
    OutputTextContent,
    OutputTranscription,
    OutputVideoContent,
    ServerReady,
    SessionEnd,
)


@dataclass
class State:
    """Track and validate events.

    Raises:
        ChatApiStateException: If the event invalidates the state.
    """

    _status: Status = field(default=Status.NOT_READY, init=False)
    _config: Config | None = field(default=None, init=False)
    _stage_id_to_stage: dict[ID, OutputStage] = field(default_factory=dict, init=False)
    _content_id_to_content: dict[ID, OutputContent] = field(
        default_factory=dict, init=False
    )
    _content_ids_with_data: set[ID] = field(default_factory=set, init=False)

    def validate(self, event: Event) -> tuple[Event, Status]:
        """Validate the event."""
        match event:
            # Server <-> Client
            case ServerReady():
                self.ready(event)
            case InputEnd():
                self.end_input(event)
            case Interrupt():
                self.interrupt(event)
            case SessionEnd():
                self.end_session(event)
            case Error():
                self.error(event)
            # Server -> Client
            case OutputTranscription():
                self.transcription(event)
            case OutputStage():
                self.stage(event)
            case OutputTextContent():
                self.content(event)
            case OutputFunctionCallContent():
                self.content(event)
            case OutputAudioContent():
                self.content(event)
            case OutputVideoContent():
                self.content(event)
            case OutputContentAddition():
                self.content_addition(event)
            case OutputFunctionCall():
                self.function_call(event)
            case OutputText():
                self.text(event)
            case OutputMedia():
                self.media(event)
            case OutputEnd():
                self.end_output(event)
            # Client -> Server
            case Config():
                self.config(event)
            case InputText():
                self.text(event)
            case InputMedia():
                self.media(event)
            case _:
                raise ChatApiStateException(f"Unknown event: {event}")

        return event, self._status

    def config(self, event: Config) -> None:
        """Set the config."""
        if self._status not in (Status.NOT_READY, Status.READY):
            raise ChatApiStateException(
                f"Cannot set config while status is {self._status.name}."
                " Status must be NOT_READY or READY."
            )

        self._status = Status.GETTING_READY
        self._config = event

    def ready(self, event: ServerReady) -> None:
        """Mark the server as ready to receive input."""
        del event

        if self._status != Status.GETTING_READY:
            raise ChatApiStateException(
                f"Cannot mark server as ready while status is {self._status.name}."
                " Status must be GETTING_READY."
            )

        self._status = Status.READY

    def end_input(self, event: InputEnd) -> None:
        """End the input."""
        del event

        if self._status != Status.INPUT:
            raise ChatApiStateException(
                f"Cannot end input while status is {self._status.name}."
                " Status must be INPUT."
            )

        self._status = Status.OUTPUT

    def interrupt(self, event: Interrupt) -> None:
        """Interrupt the request."""
        del event

        if self._status == Status.END:
            raise ChatApiStateException(
                "Cannot interrupt. Session has already been ended (Status.END)."
            )

        self._status = Status.GETTING_READY if self._config else Status.NOT_READY
        self._clear()

    def end_output(self, event: OutputEnd) -> None:
        """End the output."""
        del event

        if self._status != Status.OUTPUT:
            raise ChatApiStateException(
                f"Cannot end output while status is {self._status.name}."
                " Status must be OUTPUT."
            )

        if len(self._content_ids_with_data) != len(self._content_id_to_content):
            ids_without_data = (
                set(self._content_id_to_content.keys()) - self._content_ids_with_data
            )
            raise ChatApiStateException(
                "All content must have data before ending the output. "
                f"Content with ids {ids_without_data} have no data."
            )

        self._status = Status.GETTING_READY
        self._clear()

    def end_session(self, event: SessionEnd) -> None:
        """End the session."""
        del event

        if self._status == Status.END:
            raise ChatApiStateException(
                "Cannot end session. Session has already been ended (Status.END)."
            )

        self._status = Status.END
        self._clear()

    def error(self, event: Error) -> None:
        """Errors are time-invariant"""
        del event

    def transcription(self, event: OutputTranscription) -> None:
        """Send a transcription."""
        del event

        if self._config and self._config.input_mode != InputMode.AUDIO:
            raise ChatApiStateException(
                "Cannot send transcription. Configured input mode must be audio."
            )

        # TODO: Constrain status.

    def stage(self, event: OutputStage) -> None:
        """Send a stage."""
        if self._status != Status.OUTPUT:
            raise ChatApiStateException(
                f"Cannot send stage while status is {self._status.name}."
                " Status must be OUTPUT."
            )

        if event.id in self._stage_id_to_stage:
            raise ChatApiStateException(
                f"Stage with id {event.id} already sent. Stages must have unique ids."
            )

        self._status = Status.OUTPUT
        self._stage_id_to_stage[event.id] = event

    def content(self, event: OutputContent) -> None:
        """Send a content."""
        if self._status != Status.OUTPUT:
            raise ChatApiStateException(
                f"Cannot send content while status is {self._status.name}."
                " Status must be OUTPUT."
            )

        if event.id in self._content_id_to_content:
            raise ChatApiStateException(
                f"Content with id {event.id} already sent. Contents must have unique ids."
            )

        if (
            event.type == ContentType.AUDIO
            and self._config
            and not self._config.output_audio
        ):
            raise ChatApiStateException(
                "Cannot send audio content. Output audio is not enabled in the config."
            )

        if (
            event.type == ContentType.VIDEO
            and self._config
            and not self._config.output_video
        ):
            raise ChatApiStateException(
                "Cannot send video content. Output video is not enabled in the config."
            )

        self._status = Status.OUTPUT
        self._content_id_to_content[event.id] = event

    def content_addition(self, event: OutputContentAddition) -> None:
        """Send a content addition."""
        if self._status != Status.OUTPUT:
            raise ChatApiStateException(
                f"Cannot send content addition while status is {self._status.name}."
                " Status must be OUTPUT."
            )

        if event.content_id not in self._content_id_to_content:
            raise ChatApiStateException(
                f"Content with id {event.content_id} not found. "
                "Content must be sent before sending content addition."
            )

    def function_call(self, event: OutputFunctionCall) -> None:
        """Send a function call."""
        if self._status != Status.OUTPUT:
            raise ChatApiStateException(
                f"Cannot send function call while status is {self._status.name}."
                " Status must be OUTPUT."
            )

        if event.content_id not in self._content_id_to_content:
            raise ChatApiStateException(
                f"Content with id {event.content_id} not found. "
                "Content must be sent before sending function call."
            )

        content_type = self._content_id_to_content[event.content_id].type
        if content_type != ContentType.FUNCTION_CALL:
            raise ChatApiStateException(
                f"Cannot send function call for content with id {event.content_id}. "
                f"Content type must be {ContentType.FUNCTION_CALL.name} but "
                f"but content with id {event.content_id} has type {content_type.name}."
            )

        self._content_ids_with_data.add(event.content_id)

    def text(self, event: InputText | OutputText) -> None:
        """Send a text."""
        match event:
            case InputText():
                self.input_text(event)
            case OutputText():
                self.output_text(event)
            case _:
                raise ChatApiStateException(f"Unknown event: {event}")

    def input_text(self, event: InputText) -> None:
        """Send an input text."""
        del event

        if self._status not in (Status.READY, Status.INPUT):
            raise ChatApiStateException(
                f"Cannot send input text while status is {self._status.name}."
                " Status must be READY or INPUT."
            )

        if self._config and self._config.input_mode != InputMode.TEXT:
            raise ChatApiStateException(
                "Cannot send input text. Configured input mode must be text."
            )

        self._status = Status.INPUT

    def output_text(self, event: OutputText) -> None:
        """Send an output text."""
        if self._status != Status.OUTPUT:
            raise ChatApiStateException(
                f"Cannot send output text while status is {self._status.name}."
                " Status must be OUTPUT."
            )

        if event.content_id not in self._content_id_to_content:
            raise ChatApiStateException(
                f"Content with id {event.content_id} not found. "
                "Content must be sent before sending output text."
            )

        content_type = self._content_id_to_content[event.content_id].type
        if content_type != ContentType.TEXT:
            raise ChatApiStateException(
                f"Cannot send output text for content with id {event.content_id}. "
                f"Content type must be {ContentType.TEXT.name} but "
                f"content with id {event.content_id} has type {content_type.name}."
            )

        self._content_ids_with_data.add(event.content_id)

    def media(self, event: InputMedia | OutputMedia) -> None:
        """Send a media."""
        match event:
            case InputMedia():
                self.input_media(event)
            case OutputMedia():
                self.output_media(event)
            case _:
                raise ChatApiStateException(f"Unknown event: {event}")

    def input_media(self, event: InputMedia) -> None:
        """Send an input media."""
        del event

        if self._status not in (Status.READY, Status.INPUT):
            raise ChatApiStateException(
                f"Cannot send input media while status is {self._status.name}."
                " Status must be READY or INPUT."
            )

        if self._config and self._config.input_mode != InputMode.AUDIO:
            raise ChatApiStateException(
                "Cannot send input media. Configured input mode must be audio."
            )

        self._status = Status.INPUT

    def output_media(self, event: OutputMedia) -> None:
        """Send an output media."""
        if self._status != Status.OUTPUT:
            raise ChatApiStateException(
                f"Cannot send output media while status is {self._status.name}. "
                " Status must be OUTPUT."
            )

        if event.content_id not in self._content_id_to_content:
            raise ChatApiStateException(
                f"Content with id {event.content_id} not found. "
                "Content must be sent before sending output media."
            )

        content_type = self._content_id_to_content[event.content_id].type
        if content_type not in (ContentType.AUDIO, ContentType.VIDEO):
            raise ChatApiStateException(
                f"Cannot send output media for content with id {event.content_id}."
                f" Content type must be {ContentType.AUDIO.name} or {ContentType.VIDEO.name} but "
                f"content with id {event.content_id} has type {content_type.name}."
            )

        self._content_ids_with_data.add(event.content_id)

    def _clear(self) -> None:
        """Clear the state."""
        self._stage_id_to_stage.clear()
        self._content_id_to_content.clear()
        self._content_ids_with_data.clear()
