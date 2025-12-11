"""Process-safe handle for the client."""

from multiprocessing import Queue as ProcessQueue
from multiprocessing.shared_memory import ShareableList

from ...models import EventRequest, InputMedia, InputText, StateError
from .base import BaseInterfaceHandle


class ClientInterfaceHandle(BaseInterfaceHandle):
    """Process-safe handle for the client."""

    def __init__(
        self,
        send_queue: "ProcessQueue[EventRequest | None]",
        shared_status: ShareableList[int],
    ) -> None:
        super().__init__(
            send_queue=send_queue,
            shared_status=shared_status,
        )

    def text(self, data: str) -> InputText | StateError:
        """Send InputText."""
        event = InputText(data=data)
        return self.send(event)

    def media(
        self,
        data: bytes,
    ) -> InputMedia | StateError:
        """Send InputMedia."""
        event = InputMedia(data=data)
        return self.send(event)
