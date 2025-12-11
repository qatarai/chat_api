"""Server interface."""

from multiprocessing import Queue as ProcessQueue
from multiprocessing.shared_memory import ShareableList

from ..models import EventRequest
from .base import BaseInterface
from .handles import ServerInterfaceHandle


class ServerInterface(BaseInterface[ServerInterfaceHandle]):
    """Server interface."""

    def new_handle(
        self,
        send_queue: "ProcessQueue[EventRequest | None]",
        shared_status: ShareableList[int],
    ) -> ServerInterfaceHandle:
        return ServerInterfaceHandle(
            send_queue=send_queue,
            shared_status=shared_status,
        )
